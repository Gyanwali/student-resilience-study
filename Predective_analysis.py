import json
import random
from datetime import datetime
import plotly.express as px
import streamlit as st

# Attempt to import OpenAI for dynamic LLM integration
try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

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
# HELPER FUNCTIONS
# ──────────────────────────────────────────────
LIKERT_5 = ["1", "2", "3", "4", "5"]
COLORS = ["#2563eb", "#008080", "#d97706", "#dc2626", "#8b5cf6", "#ec4899"]


def run_model(fin):
    monthly_rent = fin["rent"] * 4.33
    monthly_groc = fin["groc"] * 4.33
    monthly_trans = fin["trans"] * 4.33
    monthly_uber = fin["uber"] * 4.33

    total_monthly_exp = (
        monthly_rent
        + monthly_groc
        + monthly_trans
        + monthly_uber
        + fin["bills"]
        + fin["remit"]
    )
    total_income = fin["income"] + (
        fin["p_amt"] if fin["p_support"] == "Yes" else 0
    )
    surplus = total_income - total_monthly_exp

    runway = (
        round(fin["savings"] / total_monthly_exp, 1)
        if total_monthly_exp > 0
        else 0
    )

    score = 50.0
    if total_income > 0:
        score += (surplus / total_income) * 30

    rent_ratio = monthly_rent / total_income if total_income > 0 else 1.0
    if rent_ratio > 0.40:
        score -= 15
    elif rent_ratio > 0.30:
        score -= 8

    if runway >= 3.0:
        score += 15
    elif runway >= 1.0:
        score += 5
    else:
        score -= 10

    if fin["meals"] == "Yes":
        score -= 10

    score = max(0, min(100, int(round(score))))

    exp_breakdown = {
        "Rent": monthly_rent,
        "Groceries": monthly_groc,
        "Transport": monthly_trans,
        "Dining/Uber": monthly_uber,
        "Bills": fin["bills"],
        "Remittance": fin["remit"],
    }

    return {
        "score": score,
        "surplus": surplus,
        "runway": runway,
        "exp_breakdown": exp_breakdown,
    }


def score_band(score):
    if score >= 75:
        return "High Resilience", "#10b981", "Strong capacity to absorb shocks."
    elif score >= 50:
        return "Moderate Resilience", "#d97706", "Stable, but vulnerable to rent hikes."
    else:
        return "Vulnerable", "#dc2626", "Elevated financial vulnerability."


# ──────────────────────────────────────────────
# AI GENERATION DIRECT CALLS
# ──────────────────────────────────────────────
def generate_ai_insights(fin_data, res):
    """Executes live API call to OpenAI GPT model."""
    if (
        HAS_OPENAI
        and "OPENAI_API_KEY" in st.secrets
        and st.secrets["OPENAI_API_KEY"]
    ):
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            prompt = f"""
            Analyze international student profile in Sydney:
            - Region: {fin_data['area']}
            - Monthly Income: ${fin_data['income']} AUD | Rent/wk: ${fin_data['rent']} AUD
            - Weekly Food Delivery/Uber: ${fin_data['uber']} AUD
            - Calculated Score: {res['score']}/100 | Monthly Surplus: ${res['surplus']:.2f}

            Provide JSON:
            {{
                "summary": "AI diagnosis of financial status in Sydney.",
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
        except Exception as e:
            st.warning(f"AI API Connection Note: Running Fallback Engine ({e})")

    # Static fallback if API Key is not set in secrets
    return {
        "summary": f"Your financial profile in {fin_data['area']} scores {res['score']}/100.",
        "risks": [
            f"Weekly Uber Eats (${fin_data['uber']}) impacts your monthly surplus."
        ],
        "actions": [
            f"Reduce food delivery by 50% to save ~${(fin_data['uber']*2.16):.0f}/month."
        ],
        "note": "To enable dynamic GPT-4 insights, add OPENAI_API_KEY to st.secrets.",
    }


def ask_ai_chatbot(query, fin_data, res):
    """Interactive Chatbot execution."""
    if (
        HAS_OPENAI
        and "OPENAI_API_KEY" in st.secrets
        and st.secrets["OPENAI_API_KEY"]
    ):
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a Sydney financial advisor AI. User context: Income=${fin_data['income']}, Rent=${fin_data['rent']}/wk in {fin_data['area']}.",
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=200,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"Error connecting to AI: {e}"

    return f"Based on your profile in {fin_data['area']}, reducing discretionary costs increases your surplus from ${res['surplus']:.2f}."


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

# ──────────────────────────────────────────────
# INTERFACE ROUTING
# ──────────────────────────────────────────────
current_step = st.session_state.step

st.markdown(
    f'<div class="top-badge">Resilience Intelligence Lab • Stage {current_step + 1} of 5</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="pid-chip">SESSION ID: {st.session_state.pid}</div>',
    unsafe_allow_html=True,
)

# Step Bar
step_bars = "".join(
    f'<div class="step {"done" if i < current_step else "active" if i == current_step else ""}"></div>'
    for i in range(5)
)
st.markdown(f'<div class="step-bar">{step_bars}</div>', unsafe_allow_html=True)

# STEP 0: CONSENT
if st.session_state.step == 0:
    st.markdown(
        '<div class="hero-title">Financial <span class="accent">Resilience</span> Study</div>',
        unsafe_allow_html=True,
    )
    with st.form("consent_form"):
        st.write("Welcome to the study. Please provide your consent to begin.")
        consent = st.checkbox("I agree to participate in this study.")
        if st.form_submit_button("Continue"):
            if consent:
                st.session_state.step = 1
                st.rerun()

# STEP 1: PRE-EXPOSURE
elif st.session_state.step == 1:
    st.markdown(
        '<div class="hero-title">Baseline <span class="accent">Assessment</span></div>',
        unsafe_allow_html=True,
    )
    with st.form("pre_form"):
        pre_trust = st.radio(
            "How much do you trust AI systems for financial analysis?", LIKERT_5
        )
        if st.form_submit_button("Next"):
            st.session_state.inputs["pre_trust"] = pre_trust
            st.session_state.step = 2
            st.rerun()

# STEP 2: INPUT QUESTIONNAIRE
elif st.session_state.step == 2:
    st.markdown(
        '<div class="hero-title">Financial <span class="accent">Profile</span></div>',
        unsafe_allow_html=True,
    )
    with st.form("financial_form"):
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox(
                "Sydney Area",
                [
                    "City / CBD",
                    "Inner West",
                    "Eastern Suburbs",
                    "North Shore",
                    "Western Sydney",
                ],
            )
            income = st.number_input("Monthly Income (AUD)", value=2800.0)
            rent = st.number_input("Weekly Rent (AUD)", value=350.0)
            groc = st.number_input("Weekly Groceries (AUD)", value=120.0)
        with col2:
            trans = st.number_input("Weekly Transport (AUD)", value=40.0)
            uber = st.number_input(
                "Weekly UberEats/Dining (AUD)", value=60.0
            )
            bills = st.number_input("Monthly Bills (AUD)", value=150.0)
            savings = st.number_input("Total Savings (AUD)", value=1500.0)

        meals = st.radio("Skipped meals due to cost?", ["No", "Yes"])

        if st.form_submit_button("Generate AI Diagnostic →"):
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
                "p_support": "No",
                "p_amt": 0,
                "remit": 0,
            }
            st.session_state.inputs.update(fin_data)
            st.session_state.results = run_model(fin_data)

            # Trigger AI model execution immediately
            st.session_state.ai_insights = generate_ai_insights(
                fin_data, st.session_state.results
            )
            st.session_state.step = 3
            st.rerun()

# STEP 3: AI DIAGNOSTIC REPORT
elif st.session_state.step == 3:
    res = st.session_state.results
    ai = st.session_state.ai_insights
    band_title, band_color, _ = score_band(res["score"])

    st.markdown(
        '<div class="hero-title">AI Diagnostic <span class="accent">Report</span></div>',
        unsafe_allow_html=True,
    )

    # Display Calculated Metrics
    st.markdown(
        f"""
    <div class="metric-grid">
        <div class="metric-card">
            <span class="metric-value" style="color:{band_color};">{res['score']}/100</span>
            <span class="metric-label">Resilience Score</span>
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

    # RENDER AI GENERATED INSIGHTS
    st.markdown("### 🤖 Generative AI Evaluation")
    st.info(f"**AI Assessment:** {ai['summary']}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Identified Risk Factors:**")
        for risk in ai["risks"]:
            st.markdown(
                f'<div class="rec-card"><div class="rec-body">⚠️ {risk}</div></div>',
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown("**AI Priority Recommendations:**")
        for action in ai["actions"]:
            st.markdown(
                f'<div class="rec-card" style="border-left-color: #10b981;"><div class="rec-body">🎯 {action}</div></div>',
                unsafe_allow_html=True,
            )

    st.caption(f"💡 *AI Note:* {ai['note']}")

    # INTERACTIVE AI CHATBOT (UNCOUPLED FROM FORM FOR REAL-TIME INTERACTION)
    st.markdown("---")
    st.markdown("### 💬 Ask the AI Assistant")

    user_query = st.text_input("Ask a question about your financial profile:")
    if st.button("Ask AI"):
        if user_query:
            reply = ask_ai_chatbot(
                user_query, st.session_state.inputs, res
            )
            st.session_state.chat_history.append((user_query, reply))

    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")

    st.markdown("---")

    # POST-EXPOSURE EVALUATION FORM
    with st.form("post_form"):
        st.markdown("### Post-Exposure Survey")
        post_trust = st.radio(
            "After seeing the AI Insights, how much do you trust this tool?",
            LIKERT_5,
        )
        pu_useful = st.radio(
            "Did you find this AI diagnostic useful?", LIKERT_5
        )

        if st.form_submit_button("Submit Evaluation →"):
            st.session_state.inputs["post_trust"] = post_trust
            st.session_state.inputs["pu_useful"] = pu_useful
            st.session_state.step = 4
            st.rerun()

# STEP 4: COMPLETION
elif st.session_state.step == 4:
    st.markdown(
        '<div class="hero-title">Study <span class="accent">Completed</span></div>',
        unsafe_allow_html=True,
    )
    st.success("Your responses have been recorded. Thank you for participating!")

    if st.button("Restart Session"):
        st.session_state.clear()
        st.rerun()
