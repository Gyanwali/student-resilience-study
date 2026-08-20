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
# PAGE CONFIGURATION
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Resilience Intelligence Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS Styling
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
    .pre-notice {
        background: #eff6ff;
        border-left: 4px solid #2563eb;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 20px;
        font-size: 0.95rem;
    }
    .scale-block {
        background: #ffffff;
        border: 1px solid var(--border-color);
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
    }
    .scale-q {
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 4px;
    }
    .scale-cite {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 12px;
    }
    .scale-anchors {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 4px;
    }
    
    .section-header {
        font-weight: 700;
        font-size: 1.1rem;
        margin-top: 16px;
        margin-bottom: 12px;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 4px;
        color: #1e293b;
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
    
    .analysis-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 0.95rem;
    }
    .rec-card {
        background: #fff;
        border-left: 4px solid #ef4444;
        border: 1px solid var(--border-color);
        border-left-width: 4px;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .rec-body {
        font-size: 0.9rem;
        color: #334155;
    }
    .explain-box {
        background: #f1f5f9;
        padding: 14px;
        border-radius: 8px;
        margin-top: 16px;
        font-size: 0.85rem;
        color: #475569;
    }
    .explain-title {
        font-weight: 700;
        margin-bottom: 4px;
    }
    .unlock-banner {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin: 24px 0;
    }
    .ub-eyebrow {
        color: #38bdf8;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.1em;
    }
    .ub-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin: 4px 0;
    }
    .ub-sub {
        font-size: 0.9rem;
        color: #94a3b8;
    }
    
    .finish-score-ring {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 6px solid #10b981;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 20px auto;
    }
    .finish-score-num {
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1;
    }
    .finish-score-lbl {
        font-size: 0.65rem;
        color: #64748b;
        text-transform: uppercase;
    }
    .finish-band {
        text-align: center;
        font-weight: 700;
        font-size: 1.2rem;
        margin-bottom: 12px;
    }
    .finish-insight {
        text-align: center;
        color: #475569;
        margin-bottom: 16px;
    }
    .finish-id {
        text-align: center;
        font-family: monospace;
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 24px;
    }
    .withdrawal-box {
        background: #fef2f2;
        border: 1px solid #fecaca;
        padding: 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #991b1b;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# CONSTANTS & CONFIGURATIONS
# ──────────────────────────────────────────────
LIKERT_5 = ["1", "2", "3", "4", "5"]
COLORS = ["#2563eb", "#008080", "#d97706", "#dc2626", "#8b5cf6", "#ec4899"]
CHART_LAYOUT = dict(
    margin=dict(l=20, r=20, t=30, b=20),
    height=260,
    showlegend=True,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


# ──────────────────────────────────────────────
# HELPER FUNCTIONS & MODEL LOGIC
# ──────────────────────────────────────────────
def connect_to_sheet():
    """Mock/Placeholder function for Google Sheet connection."""
    return True


def append_and_get_row(sheet, row_data):
    """Simulates appending a row to Google Sheets and returning the row index."""
    return random.randint(2, 500)


def run_model(fin):
    """Calculates economic financial resilience score based on user metrics."""
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

    # Base Resilience Score Calculation
    score = 50.0

    # Surplus impact
    if total_income > 0:
        surplus_ratio = surplus / total_income
        score += surplus_ratio * 30

    # Housing Stress (30/40 rule)
    rent_ratio = monthly_rent / total_income if total_income > 0 else 1.0
    if rent_ratio > 0.40:
        score -= 15
    elif rent_ratio > 0.30:
        score -= 8

    # Savings Buffer Runway
    if runway >= 3.0:
        score += 15
    elif runway >= 1.0:
        score += 5
    else:
        score -= 10

    # Meal skipping penalty
    if fin["meals"] == "Yes":
        score -= 10

    score = max(0, min(100, int(round(score))))

    flags = []
    if rent_ratio > 0.30:
        flags.append(
            f"<b>Housing Stress Warning:</b> Your rent accounts for {rent_ratio:.0%} of your total monthly income (Threshold is 30%)."
        )
    if monthly_uber > (0.15 * total_income) and total_income > 0:
        flags.append(
            f"<b>High Food Delivery Expense:</b> UberEats/Dining (${monthly_uber:.0f}/mo) represents a significant portion of income."
        )
    if runway < 1.0:
        flags.append(
            "<b>Low Emergency Buffer:</b> Your total savings cover less than 1 month of living expenses."
        )

    exp_breakdown = {
        "Rent": monthly_rent,
        "Groceries": monthly_groc,
        "Transport": monthly_trans,
        "Dining/Uber": monthly_uber,
        "Bills & Subs": fin["bills"],
        "Remittance": fin["remit"],
    }

    return {
        "score": score,
        "surplus": surplus,
        "runway": runway,
        "flags": flags,
        "exp_breakdown": exp_breakdown,
        "total_exp": total_monthly_exp,
    }


def score_band(score):
    """Maps score to risk tier."""
    if score >= 75:
        return (
            "High Resilience",
            "#10b981",
            "Your financial baseline indicates strong capacity to absorb unexpected economic shocks.",
        )
    elif score >= 50:
        return (
            "Moderate Resilience",
            "#d97706",
            "Your financial baseline is stable but vulnerable to sharp rent or living expense increases.",
        )
    else:
        return (
            "Vulnerable",
            "#dc2626",
            "Your profile displays elevated financial stress and immediate vulnerability to unexpected expenses.",
        )


# ──────────────────────────────────────────────
# AI INTEGRATION FUNCTIONS
# ──────────────────────────────────────────────
def generate_ai_insights(fin_data, res):
    """Generates dynamic AI financial diagnostic using OpenAI (with static fallback)."""
    if (
        HAS_OPENAI
        and "OPENAI_API_KEY" in st.secrets
        and st.secrets["OPENAI_API_KEY"]
    ):
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            system_prompt = (
                "You are an empathetic, highly analytical AI financial advisor specializing in Sydney's international student economy. "
                "Analyze the user's financial profile and produce personalized, location-aware insights in strict JSON format."
            )
            user_prompt = f"""
            Profile:
            - Sydney Region: {fin_data['area']}
            - Months in Sydney: {fin_data['months']}
            - Monthly Net Income: ${fin_data['income']}
            - Weekly Rent: ${fin_data['rent']} | Weekly Delivery/Uber: ${fin_data['uber']}
            - Savings Buffer: ${fin_data['savings']}
            - Resilience Score: {res['score']}/100
            - Monthly Net Surplus: ${res['surplus']:.2f}
            - Savings Runway: {res['runway']} months

            Return JSON matching this exact structure:
            {{
                "summary": "2-sentence tailored evaluation of their resilience status in Sydney.",
                "risks": ["Specific risk factor 1 based on location/spending", "Specific risk factor 2"],
                "actions": ["Actionable AUD saving step 1", "Actionable AUD saving step 2"],
                "note": "Empathetic closing encouraging statement."
            }}
            """
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            pass  # Fall back to static generation if API call fails

    # Rule-Based Dynamic Fallback
    summary = f"Based on living in {fin_data['area']} for {fin_data['months']} months, your financial resilience score is {res['score']}/100 with a monthly surplus of ${res['surplus']:,.0f}."
    risks = []
    actions = []

    if fin_data["uber"] > 50:
        risks.append(
            f"Food delivery spending in {fin_data['area']} totals ~${fin_data['uber']*4.33:.0f}/month."
        )
        actions.append(
            f"Reduce food delivery by half to save ~${(fin_data['uber']*2.16):.0f}/month."
        )

    if res["runway"] < 2.0:
        risks.append(
            f"Your emergency buffer covers only {res['runway']} months of expenses in Sydney."
        )
        actions.append(
            f"Aim to redirect ${max(50, res['surplus']*0.3):.0f} per month toward your emergency savings buffer."
        )

    if not risks:
        risks.append("No immediate high-severity risk factors detected.")
        actions.append(
            "Maintain current budget ratios and allocate extra surplus into high-yield savings."
        )

    return {
        "summary": summary,
        "risks": risks,
        "actions": actions,
        "note": "Small, consistent adjustments to discretionary spending build long-term economic resilience.",
    }


def ask_ai_chatbot(user_query, fin_data, res):
    """Handles interactive conversational AI query."""
    if (
        HAS_OPENAI
        and "OPENAI_API_KEY" in st.secrets
        and st.secrets["OPENAI_API_KEY"]
    ):
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            system_prompt = (
                f"You are the Resilience Intelligence AI Assistant. Answer student financial questions concisely based on their profile: "
                f"Income ${fin_data['income']}/mo, Rent ${fin_data['rent']}/wk in {fin_data['area']}, Savings ${fin_data['savings']}, "
                f"Resilience Score {res['score']}/100, Surplus ${res['surplus']:.2f}/mo."
            )
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.7,
                max_tokens=250,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI Assistant Service temporarily unavailable: {e}"

    # Fallback answer
    return (
        f"Based on your profile in {fin_data['area']} (Income: ${fin_data['income']}/mo, Weekly Rent: ${fin_data['rent']}), "
        f"your calculated monthly surplus is ${res['surplus']:,.2f}. To optimize this, focus on controlling discretionary expenses like dining/delivery."
    )


# ──────────────────────────────────────────────
# STATE MANAGEMENT
# ──────────────────────────────────────────────
if "pid" not in st.session_state:
    st.session_state.pid = f"PID-{random.randint(1000, 9999)}"
if "step" not in st.session_state:
    st.session_state.step = 0
if "inputs" not in st.session_state:
    st.session_state.inputs = {}
if "results" not in st.session_state:
    st.session_state.results = None
if "row_id" not in st.session_state:
    st.session_state.row_id = None
if "sheet" not in st.session_state:
    st.session_state.sheet = None
if "survey_submitted" not in st.session_state:
    st.session_state.survey_submitted = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Connect to sheet once
if st.session_state.sheet is None:
    st.session_state.sheet = connect_to_sheet()


# ──────────────────────────────────────────────
# MAIN APP FLOW
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

# Visual step bar
step_bars = ""
for i in range(5):
    if i < current_step:
        step_bars += '<div class="step done"></div>'
    elif i == current_step:
        step_bars += '<div class="step active"></div>'
    else:
        step_bars += '<div class="step"></div>'
st.markdown(f'<div class="step-bar">{step_bars}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
# STEP 0: CONSENT & PARTICIPATION
# ══════════════════════════════════════════════
if st.session_state.step == 0:
    st.markdown(
        '<div class="hero-title">Financial <span class="accent">Resilience</span> Study</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">Evaluating personal financial stress and decision-making support systems among international students in Sydney.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="card">
        <h3>Participant Information & Informed Consent</h3>
        <p>You are invited to participate in a research study analyzing financial vulnerability, housing stress, and the perceived usefulness of AI-driven financial diagnostic tools. This study is conducted for research purposes at Excelsia College.</p>
        
        <h4>What to Expect:</h4>
        <ul>
            <li><b>Pre-Exposure Survey:</b> Brief baseline question regarding AI technology trust.</li>
            <li><b>Financial Questionnaire:</b> ~3-minute survey capturing non-identifiable financial metrics (income, rent, savings, location).</li>
            <li><b>AI Diagnostic & Post-Exposure Survey:</b> Immediate personalized financial breakdown followed by a brief evaluation of the diagnostic output.</li>
        </ul>

        <h4>Data Privacy & Anonymity:</h4>
        <p>No directly identifying personal details (such as your full name, email address, or exact street address) will be recorded. All data is collected using a randomized Session ID for aggregation and statistical analysis.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.form("consent_form"):
        consent_given = st.checkbox(
            "I agree to participate voluntarily and understand that my responses are anonymous and collected solely for academic research."
        )
        submit_consent = st.form_submit_button("Continue to Baseline Survey →")

        if submit_consent:
            if consent_given:
                st.session_state.inputs["consent"] = "Yes"
                st.session_state.step = 1
                st.rerun()
            else:
                st.error("⚠️ Consent is required to participate in this study.")


# ══════════════════════════════════════════════
# STEP 1: PRE-EXPOSURE BASELINE SURVEY
# ══════════════════════════════════════════════
elif st.session_state.step == 1:
    st.markdown(
        '<div class="hero-title">Baseline <span class="accent">Assessment</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">Before proceeding to the financial tool, please indicate your baseline view.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="pre-notice">
        <b>Pre-Exposure Control Metric:</b> This single question establishes your baseline trust in automated AI systems before seeing any customized financial insights.
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.form("pre_survey_form"):
        st.markdown('<div class="scale-block">', unsafe_allow_html=True)
        st.markdown(
            '<div class="scale-q">Prior to using this diagnostic tool, how much do you generally trust AI systems to analyze personal financial data accurately?</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="scale-cite">Single-item pre-exposure trust baseline (1 = Low Trust, 5 = High Trust)</div>',
            unsafe_allow_html=True,
        )
        pre_ai_trust = st.radio(
            "Pre-AI Trust Level",
            LIKERT_5,
            index=2,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="scale-anchors"><span>1 - Very Low Trust</span><span>3 - Neutral</span><span>5 - Very High Trust</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        submit_pre = st.form_submit_button(
            "Proceed to Financial Questionnaire →"
        )

        if submit_pre:
            st.session_state.inputs["pre_ai_trust"] = pre_ai_trust
            st.session_state.step = 2
            st.rerun()


# ══════════════════════════════════════════════
# STEP 2: FINANCIAL PROFILE QUESTIONNAIRE
# ══════════════════════════════════════════════
elif st.session_state.step == 2:
    st.markdown(
        '<div class="hero-title">Financial <span class="accent">Profile</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">Provide your approximate financial details in AUD. Responses are completely anonymous.</div>',
        unsafe_allow_html=True,
    )

    with st.form("financial_profile_form"):
        st.markdown(
            '<div class="section-header">Demographics & Location</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox(
                "Sydney Area / Region",
                [
                    "City / CBD",
                    "Inner West",
                    "Eastern Suburbs",
                    "North Shore",
                    "Western Sydney",
                    "South Sydney",
                    "Outside Sydney",
                ],
            )
        with col2:
            months = st.number_input(
                "Months Living in Sydney",
                min_value=1,
                max_value=240,
                value=12,
                step=1,
            )

        st.markdown(
            '<div class="section-header">Income & Support</div>',
            unsafe_allow_html=True,
        )
        col3, col4 = st.columns(2)
        with col3:
            income = st.number_input(
                "Monthly Income (AUD, net/after tax)",
                min_value=0.0,
                value=2800.0,
                step=100.0,
            )
            p_support = st.radio(
                "Do you receive regular financial support from parents/family?",
                ["No", "Yes"],
                horizontal=True,
            )
        with col4:
            p_amt = 0.0
            if p_support == "Yes":
                p_amt = st.number_input(
                    "Monthly Family Support Amount (AUD)",
                    min_value=0.0,
                    value=500.0,
                    step=50.0,
                )
            lit = st.selectbox(
                "Self-Rated Financial Literacy",
                ["Novice", "Intermediate", "Advanced"],
            )

        st.markdown(
            '<div class="section-header">Fixed & Discretionary Expenses</div>',
            unsafe_allow_html=True,
        )
        col5, col6 = st.columns(2)
        with col5:
            rent = st.number_input(
                "Weekly Rent / Housing (AUD)",
                min_value=0.0,
                value=350.0,
                step=10.0,
            )
            groc = st.number_input(
                "Weekly Groceries (AUD)",
                min_value=0.0,
                value=120.0,
                step=10.0,
            )
            trans = st.number_input(
                "Weekly Public Transport / Fuel (AUD)",
                min_value=0.0,
                value=40.0,
                step=5.0,
            )
        with col6:
            uber = st.number_input(
                "Weekly UberEats / Dining Out / Delivery (AUD)",
                min_value=0.0,
                value=60.0,
                step=10.0,
            )
            bills = st.number_input(
                "Monthly Utilities & Subscriptions (AUD)",
                min_value=0.0,
                value=150.0,
                step=10.0,
            )
            remit = st.number_input(
                "Monthly Money Sent Home / Remittance (AUD)",
                min_value=0.0,
                value=0.0,
                step=50.0,
            )

        st.markdown(
            '<div class="section-header">Savings & Food Security</div>',
            unsafe_allow_html=True,
        )
        col7, col8 = st.columns(2)
        with col7:
            savings = st.number_input(
                "Total Emergency Savings Buffer (AUD)",
                min_value=0.0,
                value=1500.0,
                step=100.0,
            )
        with col8:
            meals = st.radio(
                "In the past 12 months, have you skipped meals due to financial pressure?",
                ["No", "Yes"],
                horizontal=True,
            )

        submit_fin = st.form_submit_button(
            "Generate AI Diagnostic Report →"
        )

        if submit_fin:
            fin_data = {
                "income": income,
                "rent": rent,
                "uber": uber,
                "groc": groc,
                "trans": trans,
                "bills": bills,
                "p_support": p_support,
                "p_amt": p_amt,
                "savings": savings,
                "remit": remit,
                "lit": lit,
                "area": area,
                "months": months,
                "meals": meals,
            }
            st.session_state.inputs.update(fin_data)

            # Run model
            results = run_model(fin_data)
            st.session_state.results = results

            # Initial sheet record creation
            if st.session_state.sheet and st.session_state.row_id is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row_data = [
                    st.session_state.pid,
                    timestamp,
                    st.session_state.inputs.get("consent"),
                    rent,
                    income,
                    area,
                    uber,
                    "",
                    "",
                    results["score"],
                    meals,
                    p_support,
                    remit,
                    p_amt,
                    savings,
                    trans,
                    lit,
                    months,
                    "",
                    st.session_state.inputs.get("pre_ai_trust"),
                    "",
                    "",
                    "",
                ]
                row_idx = append_and_get_row(st.session_state.sheet, row_data)
                st.session_state.row_id = row_idx

            st.session_state.step = 3
            st.rerun()


# ══════════════════════════════════════════════
# STEP 3: AI DIAGNOSTIC REPORT & POST-EXPOSURE EVALUATION
# ══════════════════════════════════════════════
elif st.session_state.step == 3:
    res = st.session_state.results
    band_title, band_color, band_desc = score_band(res["score"])

    st.markdown(
        '<div class="hero-title">Diagnostic <span class="accent">Report</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">AI-generated financial resilience diagnostic based on your submitted metrics.</div>',
        unsafe_allow_html=True,
    )

    # Top Metric Grid
    st.markdown(
        f"""
    <div class="metric-grid">
        <div class="metric-card">
            <span class="metric-value" style="color: {band_color};">{res['score']}<span style="font-size:1.2rem;">/100</span></span>
            <span class="metric-label">Resilience Index</span>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color: var(--teal);">${res['surplus']:,.0f}</span>
            <span class="metric-label">Monthly Net Surplus</span>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color: var(--amber);">{res['runway']} <span style="font-size:1rem;">mo</span></span>
            <span class="metric-label">Emergency Runway</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Diagnostic Summary Box
    st.markdown(
        f"""
    <div class="analysis-box">
        <span style="color:{band_color}; font-weight:bold;">STATUS: {band_title.upper()}</span><br/>
        {band_desc}
    </div>
    """,
        unsafe_allow_html=True,
    )

    # DYNAMIC GENERATIVE AI INSIGHTS
    with st.spinner("🤖 AI Diagnostic Engine generating personalized analysis..."):
        ai_insights = generate_ai_insights(st.session_state.inputs, res)

    st.markdown("### 🤖 Personalized Generative AI Insights")
    st.info(f"**AI Assessment:** {ai_insights['summary']}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Identified Risk Factors:**")
        for risk in ai_insights["risks"]:
            st.markdown(
                f'<div class="rec-card"><div class="rec-body">⚠️ {risk}</div></div>',
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown("**Recommended Priority Actions:**")
        for act in ai_insights["actions"]:
            st.markdown(
                f'<div class="rec-card" style="border-left-color: #10b981;"><div class="rec-body">🎯 {act}</div></div>',
                unsafe_allow_html=True,
            )

    st.caption(f"💡 *Note:* {ai_insights['note']}")

    # INTERACTIVE AI CHATBOT
    st.markdown("---")
    st.markdown("### 💬 Ask the AI Financial Assistant")
    st.markdown(
        "Have questions about your report or need specific budgeting strategies for Sydney?"
    )

    user_query = st.text_input(
        "Type your question below:",
        placeholder="e.g., How can I reduce my weekly expenses in Sydney?",
    )
    if user_query:
        with st.spinner("AI Assistant is analyzing..."):
            reply = ask_ai_chatbot(user_query, st.session_state.inputs, res)
            st.session_state.chat_history.append((user_query, reply))

    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI Assistant:** {a}")
        st.markdown("---")

    # Expense Breakdown Chart
    st.markdown(
        '<div class="section-header">Expense Breakdown</div>',
        unsafe_allow_html=True,
    )
    fig = px.pie(
        names=list(res["exp_breakdown"].keys()),
        values=list(res["exp_breakdown"].values()),
        color_discrete_sequence=COLORS,
        hole=0.4,
    )
    fig.update_layout(CHART_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="explain-box">', unsafe_allow_html=True)
    st.markdown(
        '<div class="explain-title">Model Framework & Academic Citation</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    This resilience model evaluates cash surplus (Carroll 1997), housing stress thresholds (AHURI 2023), 
    and emergency buffer capacity (Deaton 1991). The score reflects your structural capacity to withstand 
    unforeseen financial shocks in Sydney's urban economy.
    """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Unlock Banner for Post-Survey
    st.markdown(
        """
    <div class="unlock-banner">
        <div class="ub-eyebrow">FINAL RESEARCH STEP</div>
        <div class="ub-title">Post-Exposure Evaluation Survey</div>
        <div class="ub-sub">Please evaluate the usefulness and trustworthiness of the diagnostic tool above to complete the study.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Post-Exposure Survey Form
    with st.form("post_exposure_survey"):
        st.markdown(
            '<div class="section-header">Post-Exposure Evaluation</div>',
            unsafe_allow_html=True,
        )

        # Q1: POST_AITrust
        st.markdown('<div class="scale-block">', unsafe_allow_html=True)
        st.markdown(
            '<div class="scale-q">1. After reviewing this diagnostic report, how much do you trust the accuracy and objectivity of this AI tool?</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="scale-cite">Post-exposure Trust Scale (1 = Low Trust, 5 = High Trust)</div>',
            unsafe_allow_html=True,
        )
        post_ai_trust = st.radio(
            "POST_AITrust",
            LIKERT_5,
            index=3,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="scale-anchors"><span>1 - Strongly Disagree</span><span>3 - Neutral</span><span>5 - Strongly Agree</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Q2: POST_PU_Understanding
        st.markdown('<div class="scale-block">', unsafe_allow_html=True)
        st.markdown(
            '<div class="scale-q">2. This diagnostic report helped me better understand my current financial condition.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="scale-cite">Perceived Usefulness - Dimension 1 (TAM Scale)</div>',
            unsafe_allow_html=True,
        )
        pu_understanding = st.radio(
            "POST_PU_Understanding",
            LIKERT_5,
            index=3,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="scale-anchors"><span>1 - Strongly Disagree</span><span>3 - Neutral</span><span>5 - Strongly Agree</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Q3: POST_PU_Useful
        st.markdown('<div class="scale-block">', unsafe_allow_html=True)
        st.markdown(
            '<div class="scale-q">3. Overall, I found this AI financial diagnostic tool useful.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="scale-cite">Perceived Usefulness - Dimension 2 (TAM Scale)</div>',
            unsafe_allow_html=True,
        )
        pu_useful = st.radio(
            "POST_PU_Useful",
            LIKERT_5,
            index=3,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="scale-anchors"><span>1 - Strongly Disagree</span><span>3 - Neutral</span><span>5 - Strongly Agree</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Q4: POST_PU_DecisionAid
        st.markdown('<div class="scale-block">', unsafe_allow_html=True)
        st.markdown(
            '<div class="scale-q">4. The insights provided would assist me in making better financial decisions in the future.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="scale-cite">Perceived Usefulness - Dimension 3 (TAM Scale)</div>',
            unsafe_allow_html=True,
        )
        pu_decision_aid = st.radio(
            "POST_PU_DecisionAid",
            LIKERT_5,
            index=3,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="scale-anchors"><span>1 - Strongly Disagree</span><span>3 - Neutral</span><span>5 - Strongly Agree</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Q5: Behavioural Intent
        st.markdown('<div class="scale-block">', unsafe_allow_html=True)
        st.markdown(
            '<div class="scale-q">5. How likely are you to adjust your spending or savings behavior based on this report?</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="scale-cite">Behavioural Intent Construct (1 = Unlikely, 5 = Highly Likely)</div>',
            unsafe_allow_html=True,
        )
        beh_intent = st.radio(
            "Behavioural Intent",
            LIKERT_5,
            index=3,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="scale-anchors"><span>1 - Unlikely</span><span>3 - Neutral</span><span>5 - Highly Likely</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        submit_post = st.form_submit_button(
            "Submit Evaluation & Complete Study →"
        )

        if submit_post:
            u_val = float(pu_understanding)
            use_val = float(pu_useful)
            d_val = float(pu_decision_aid)
            pu_composite = round((u_val + use_val + d_val) / 3.0, 2)

            st.session_state.inputs.update(
                {
                    "post_ai_trust": post_ai_trust,
                    "pu_understanding": pu_understanding,
                    "pu_useful": pu_useful,
                    "pu_decision_aid": pu_decision_aid,
                    "pu_composite": pu_composite,
                    "beh_intent": beh_intent,
                }
            )

            # Update Google Sheet row if row index exists
            if st.session_state.sheet and st.session_state.row_id:
                try:
                    row_idx = st.session_state.row_id
                    st.session_state.sheet.update_cell(
                        row_idx, 8, int(post_ai_trust)
                    )
                    st.session_state.sheet.update_cell(row_idx, 9, pu_composite)
                    st.session_state.sheet.update_cell(
                        row_idx, 19, int(beh_intent)
                    )
                    st.session_state.sheet.update_cell(
                        row_idx, 21, int(pu_understanding)
                    )
                    st.session_state.sheet.update_cell(
                        row_idx, 22, int(pu_useful)
                    )
                    st.session_state.sheet.update_cell(
                        row_idx, 23, int(pu_decision_aid)
                    )
                except Exception as e:
                    st.warning(
                        f"⚠️ Data updated locally, but sheet sync encountered an issue: {e}"
                    )

            st.session_state.step = 4
            st.rerun()


# ══════════════════════════════════════════════
# STEP 4: COMPLETION / THANK YOU
# ══════════════════════════════════════════════
elif st.session_state.step == 4:
    res = st.session_state.results
    band_title, band_color, _ = score_band(res["score"])

    st.markdown(
        '<div class="hero-title">Study <span class="accent">Completed</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">Thank you for contributing to this research project on international student resilience.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="finish-score-ring" style="border-color: {band_color};">
        <span class="finish-score-num" style="color: {band_color};">{res['score']}</span>
        <span class="finish-score-lbl">Resilience Score</span>
    </div>
    <div class="finish-band" style="color: {band_color};">{band_title}</div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="finish-insight">
        <b>Data Submission Confirmed:</b> Your evaluation responses and financial baseline metrics have been successfully logged anonymously.
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="finish-id">COMPLETION CONFIRMATION ID: {st.session_state.pid}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="withdrawal-box">
        <b>Need Support or Have Questions?</b><br/>
        If you experience financial hardship, please contact Excelsia College Student Support Services or national advocacy bodies such as Study NSW.
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.button("Start New Session"):
        st.session_state.clear()
        st.rerun()
