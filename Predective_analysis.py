"""
Resilience Intelligence Lab
----------------------------
A financial resilience checker for people living in Sydney (built with
international students in mind, but usable by anyone). Users enter their
income/expenses, get a resilience score, a spending breakdown, and
AI-generated (or rule-based fallback) guidance on how to improve it.
"""

import json
import logging
import random

import plotly.express as px
import streamlit as st

# Attempt to import OpenAI for dynamic LLM integration
try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resilience_lab")

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────
#
# METHODOLOGY
# The resilience score is adapted from two established, public frameworks
# rather than an invented formula:
#
# 1. The Financial Health Network's FinHealth Score (R) -- a widely used
#    framework built around four pillars: Spend, Save, Borrow, and Plan.
#    (https://finhealthnetwork.org). We adapt two of those pillars here:
#      - Spend -> whether monthly cash flow is positive or negative (surplus)
#      - Save  -> whether savings could cover a shock (emergency runway)
#    We do not collect debt/credit data, so the "Borrow" pillar is not
#    represented, and this is NOT the licensed FinHealth Score itself --
#    it's a small, unofficial approximation of the same idea.
#
# 2. HUD's housing cost-burden standard -- spending more than 30% of income
#    on housing is "cost-burdened"; more than 50% is "severely cost-burdened".
#    We use these thresholds for the rent-ratio penalty below.
#
# 3. The common "3+ months of expenses in savings" emergency-fund guideline
#    used broadly in consumer-finance education, applied to the runway bonus.
#
# This is a simplified, educational estimate -- not certified financial
# advice, and not a substitute for the full FinHealth Score survey.
WEEKS_PER_MONTH = 4.33

SCORE_BASE = 50.0
SURPLUS_WEIGHT = 30  # multiplier on (surplus / income) -- "Spend" pillar

RENT_RATIO_HIGH = 0.50  # HUD: >50% of income on housing = severely cost-burdened
RENT_RATIO_HIGH_PENALTY = 15
RENT_RATIO_MED = 0.30  # HUD: >30% of income on housing = cost-burdened
RENT_RATIO_MED_PENALTY = 8

RUNWAY_GOOD_MONTHS = 3.0  # standard emergency-fund guideline: 3+ months
RUNWAY_GOOD_BONUS = 15
RUNWAY_OK_MONTHS = 1.0
RUNWAY_OK_BONUS = 5
RUNWAY_LOW_PENALTY = 10

MEALS_SKIPPED_PENALTY = 10  # material-hardship signal

# Used to estimate savings from halving weekly discretionary spend
HALF_MONTH_MULTIPLIER = WEEKS_PER_MONTH / 2

LIKERT_5 = ["1", "2", "3", "4", "5"]
SYDNEY_AREAS = [
    "City / CBD",
    "Inner West",
    "Eastern Suburbs",
    "North Shore",
    "Western Sydney",
]

# ──────────────────────────────────────────────
# PAGE CONFIGURATION & STYLES
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Resilience Intelligence Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --teal: #008080;
        --amber: #d97706;
        --red: #dc2626;
        --bg-card: #f8fafc;
        --border-color: #e2e8f0;
    }
    .top-badge {
        font-weight: 600;
        color: #475569;
        margin-bottom: 4px;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
    }
    .pid-chip {
        display: inline-block;
        background: #e2e8f0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-family: monospace;
        margin-bottom: 12px;
    }
    .step-bar {
        display: flex;
        gap: 6px;
        margin-bottom: 24px;
    }
    .step {
        height: 6px;
        flex: 1;
        background-color: #cbd5e1;
        border-radius: 3px;
    }
    .step.active {
        background-color: #2563eb;
    }
    .step.done {
        background-color: #10b981;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .hero-title .accent {
        color: #2563eb;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 24px;
    }
    .card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .metric-grid {
        display: flex;
        gap: 16px;
        margin-bottom: 20px;
    }
    .metric-card {
        flex: 1;
        background: #ffffff;
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        display: block;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
    }
    .rec-card {
        background: #fff;
        border-left: 4px solid #ef4444;
        border: 1px solid var(--border-color);
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .rec-body {
        font-size: 0.9rem;
        color: #334155;
    }
    .unlock-banner {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin: 24px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# CORE MODEL (pure functions, no Streamlit / IO)
# ──────────────────────────────────────────────
def run_model(fin: dict) -> dict:
    """Compute expense breakdown, surplus, runway, and resilience score."""
    monthly_rent = fin["rent"] * WEEKS_PER_MONTH
    monthly_groc = fin["groc"] * WEEKS_PER_MONTH
    monthly_trans = fin["trans"] * WEEKS_PER_MONTH
    monthly_uber = fin["uber"] * WEEKS_PER_MONTH

    total_monthly_exp = (
        monthly_rent + monthly_groc + monthly_trans + monthly_uber + fin["bills"]
    )
    total_income = fin["income"]
    surplus = total_income - total_monthly_exp

    runway = round(fin["savings"] / total_monthly_exp, 1) if total_monthly_exp > 0 else 0.0

    score = SCORE_BASE
    if total_income > 0:
        score += (surplus / total_income) * SURPLUS_WEIGHT

    rent_ratio = monthly_rent / total_income if total_income > 0 else 1.0
    if rent_ratio > RENT_RATIO_HIGH:
        score -= RENT_RATIO_HIGH_PENALTY
    elif rent_ratio > RENT_RATIO_MED:
        score -= RENT_RATIO_MED_PENALTY

    if runway >= RUNWAY_GOOD_MONTHS:
        score += RUNWAY_GOOD_BONUS
    elif runway >= RUNWAY_OK_MONTHS:
        score += RUNWAY_OK_BONUS
    else:
        score -= RUNWAY_LOW_PENALTY

    if fin["meals"] == "Yes":
        score -= MEALS_SKIPPED_PENALTY

    score = max(0, min(100, int(round(score))))

    exp_breakdown = {
        "Rent": monthly_rent,
        "Groceries": monthly_groc,
        "Transport": monthly_trans,
        "Dining/Uber": monthly_uber,
        "Bills": fin["bills"],
    }

    return {
        "score": score,
        "surplus": surplus,
        "runway": runway,
        "rent_ratio": rent_ratio,
        "exp_breakdown": exp_breakdown,
        "total_monthly_exp": total_monthly_exp,
    }


def score_band(score: int) -> tuple[str, str, str]:
    if score >= 75:
        return "High Resilience", "#10b981", "Strong capacity to absorb shocks."
    elif score >= 50:
        return "Moderate Resilience", "#d97706", "Stable, but vulnerable to rent hikes."
    else:
        return "Vulnerable", "#dc2626", "Elevated financial vulnerability."


def rule_based_actions(fin: dict, res: dict) -> list[str]:
    """Concrete, deterministic guidance -- always available, even without AI."""
    actions = []
    if res["rent_ratio"] > RENT_RATIO_HIGH:
        actions.append(
            "Your rent is taking up a large share of your income. Look into "
            "share-housing, moving further from the CBD, or a rent-assistance "
            "service for students."
        )
    if fin["uber"] > 0:
        est_saving = fin["uber"] * HALF_MONTH_MULTIPLIER
        actions.append(
            f"Halving weekly food delivery/dining spend could free up roughly "
            f"${est_saving:.0f}/month."
        )
    if res["runway"] < RUNWAY_OK_MONTHS:
        actions.append(
            "You have less than a month of expenses in savings. Aim to build a "
            "small buffer first -- even $50-100/week adds up quickly."
        )
    if fin["meals"] == "Yes":
        actions.append(
            "You've reported skipping meals to save money -- this is a sign of "
            "real financial stress. Many universities and local councils offer "
            "free food pantries; it's worth checking what's available near you."
        )
    if not actions:
        actions.append("Your numbers look healthy -- keep tracking spending monthly.")
    return actions


# ──────────────────────────────────────────────
# AI GENERATION (optional; always has a safe fallback)
# ──────────────────────────────────────────────
def _openai_client_ready() -> bool:
    return HAS_OPENAI and bool(st.secrets.get("OPENAI_API_KEY"))


def generate_ai_insights(fin_data: dict, res: dict) -> dict:
    """Live OpenAI call for narrative insights, with a deterministic fallback."""
    if _openai_client_ready():
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            prompt = f"""
            Analyze this person's financial profile in Sydney:
            - Region: {fin_data['area']}
            - Monthly Income: ${fin_data['income']} AUD | Rent/wk: ${fin_data['rent']} AUD
            - Weekly Food Delivery/Uber: ${fin_data['uber']} AUD
            - Calculated Score: {res['score']}/100 | Monthly Surplus: ${res['surplus']:.2f}

            Provide JSON:
            {{
                "summary": "Plain-language diagnosis of their financial status.",
                "risks": ["Risk 1", "Risk 2"],
                "actions": ["Actionable step 1", "Actionable step 2"],
                "note": "Encouraging remark."
            }}
            """
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            logger.exception("OpenAI insight generation failed")
            st.warning(
                "AI insights are temporarily unavailable -- showing standard "
                "guidance instead."
            )

    # Deterministic fallback if no API key or the call fails
    actions = rule_based_actions(fin_data, res)
    return {
        "summary": f"Your financial profile in {fin_data['area']} scores {res['score']}/100.",
        "risks": [
            f"Weekly Uber Eats/dining (${fin_data['uber']}) is a notable share of "
            "discretionary spending."
            if fin_data["uber"] > 0
            else "No major discretionary spending risk detected."
        ],
        "actions": actions,
        "note": "Add an OPENAI_API_KEY in st.secrets to enable live AI-generated insights.",
    }


def ask_ai_chatbot(query: str, fin_data: dict, res: dict) -> str:
    if _openai_client_ready():
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a Sydney financial advisor AI. User context: "
                            f"Income=${fin_data['income']}, Rent=${fin_data['rent']}/wk "
                            f"in {fin_data['area']}."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=200,
            )
            return resp.choices[0].message.content
        except Exception:
            logger.exception("OpenAI chatbot call failed")
            return "Sorry, the AI assistant is temporarily unavailable. Please try again shortly."

    return (
        f"Based on your profile in {fin_data['area']}, reducing discretionary "
        f"costs increases your surplus from ${res['surplus']:.2f}."
    )


# ──────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ──────────────────────────────────────────────
if "pid" not in st.session_state:
    st.session_state.pid = f"PID-{random.randint(1000, 9999)}"
if "step" not in st.session_state:
    st.session_state.step = 0
if "inputs" not in st.session_state:
    st.session_state.inputs = {}
if "results" not in st.session_state:
    st.session_state.results = None
if "ai_insights" not in st.session_state:
    st.session_state.ai_insights = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

TOTAL_STEPS = 3  # Welcome -> Financial Profile -> Report

# ──────────────────────────────────────────────
# INTERFACE ROUTING
# ──────────────────────────────────────────────
current_step = st.session_state.step

st.markdown(
    f'<div class="top-badge">Resilience Intelligence Lab • Step {current_step + 1} of {TOTAL_STEPS}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="pid-chip">REPORT ID: {st.session_state.pid}</div>',
    unsafe_allow_html=True,
)

step_bars = "".join(
    f'<div class="step {"done" if i < current_step else "active" if i == current_step else ""}"></div>'
    for i in range(TOTAL_STEPS)
)
st.markdown(f'<div class="step-bar">{step_bars}</div>', unsafe_allow_html=True)

# STEP 0: WELCOME
if st.session_state.step == 0:
    st.markdown(
        '<div class="hero-title">Financial <span class="accent">Resilience</span> Check</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">Answer a few questions about your income and '
        "expenses in Sydney and get an instant resilience score, a spending "
        "breakdown, and practical next steps.</div>",
        unsafe_allow_html=True,
    )
    st.caption("Nothing you enter is stored beyond this session.")
    if st.button("Get Started →", type="primary"):
        st.session_state.step = 1
        st.rerun()

# STEP 1: INPUT QUESTIONNAIRE
elif st.session_state.step == 1:
    st.markdown(
        '<div class="hero-title">Financial <span class="accent">Profile</span></div>',
        unsafe_allow_html=True,
    )
    with st.form("financial_form"):
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox("Sydney Area", SYDNEY_AREAS)
            income = st.number_input("Monthly Income (AUD)", min_value=0.0, value=2800.0)
            rent = st.number_input("Weekly Rent (AUD)", min_value=0.0, value=350.0)
            groc = st.number_input("Weekly Groceries (AUD)", min_value=0.0, value=120.0)
        with col2:
            trans = st.number_input("Weekly Transport (AUD)", min_value=0.0, value=40.0)
            uber = st.number_input("Weekly UberEats/Dining (AUD)", min_value=0.0, value=60.0)
            bills = st.number_input("Monthly Bills (AUD)", min_value=0.0, value=150.0)
            savings = st.number_input("Total Savings (AUD)", min_value=0.0, value=1500.0)

        meals = st.radio("Skipped meals due to cost?", ["No", "Yes"])

        submitted = st.form_submit_button("Generate My Report →", type="primary")
        if submitted:
            if income <= 0:
                st.error("Please enter a monthly income greater than $0 to generate a report.")
            else:
                fin_data = {
                    "income": income,
                    "rent": rent,
                    "uber": uber,
                    "groc": groc,
                    "trans": trans,
                    "bills": bills,
                    "savings": savings,
                    "area": area,
                    "meals": meals,
                }
                st.session_state.inputs = fin_data
                st.session_state.results = run_model(fin_data)
                st.session_state.ai_insights = generate_ai_insights(
                    fin_data, st.session_state.results
                )
                st.session_state.step = 2
                st.rerun()

# STEP 2: REPORT
elif st.session_state.step == 2:
    fin = st.session_state.inputs
    res = st.session_state.results
    ai = st.session_state.ai_insights
    band_title, band_color, band_desc = score_band(res["score"])

    st.markdown(
        '<div class="hero-title">Your <span class="accent">Resilience Report</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="metric-grid">
        <div class="metric-card">
            <span class="metric-value" style="color:{band_color};">{res['score']}/100</span>
            <span class="metric-label">{band_title}</span>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color:var(--teal);">${res['surplus']:,.0f}</span>
            <span class="metric-label">Monthly Surplus</span>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color:var(--amber);">{res['runway']} mo</span>
            <span class="metric-label">Emergency Buffer</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.caption(band_desc)

    with st.expander("How is this score calculated?"):
        st.markdown(
            """
This score is an educational estimate adapted from two established, public
frameworks -- it's not a licensed financial product or professional advice.

- **Cash flow** (spend vs. income) is based on the *Spend* pillar of the
  [Financial Health Network's FinHealth Score](https://finhealthnetwork.org),
  a widely used household financial-health framework.
- **Emergency runway** (months of expenses covered by savings) reflects the
  *Save* pillar of the same framework, using the common "3+ months of
  expenses saved" guideline from consumer-finance education.
- **Housing cost burden** uses HUD's standard: spending over 30% of income
  on rent is "cost-burdened," over 50% is "severely cost-burdened."
- **Skipped meals** is treated as a signal of material financial hardship.

We don't collect debt or credit data, so this does *not* include the
"Borrow" pillar from the full FinHealth Score, and this tool is a small,
unofficial approximation -- not the official FinHealth Score survey.
            """
        )

    # Spending breakdown chart
    st.markdown("### 📊 Where Your Money Goes")
    breakdown = res["exp_breakdown"]
    fig = px.pie(
        names=list(breakdown.keys()),
        values=list(breakdown.values()),
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # AI / guidance section
    st.markdown("### 🤖 Your Diagnostic")
    st.info(f"**Assessment:** {ai['summary']}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Risk Factors:**")
        for risk in ai["risks"]:
            st.markdown(
                f'<div class="rec-card"><div class="rec-body">⚠️ {risk}</div></div>',
                unsafe_allow_html=True,
            )
    with col_b:
        st.markdown("**Recommended Actions:**")
        for action in ai["actions"]:
            st.markdown(
                f'<div class="rec-card" style="border-left-color: #10b981;"><div class="rec-body">🎯 {action}</div></div>',
                unsafe_allow_html=True,
            )

    st.caption(f"💡 {ai['note']}")

    # Interactive chatbot
    st.markdown("---")
    st.markdown("### 💬 Ask a Follow-up Question")
    user_query = st.text_input("Ask about your financial profile:")
    if st.button("Ask"):
        if user_query:
            reply = ask_ai_chatbot(user_query, fin, res)
            st.session_state.chat_history.append((user_query, reply))

    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**Assistant:** {a}")

    st.markdown("---")
    if st.button("Start a New Report"):
        st.session_state.clear()
        st.rerun()
