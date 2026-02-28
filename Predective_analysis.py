import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import math
import re
import random
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Sheet column map (1-indexed) ──────────────
# Col 1  → Unique_ID
# Col 2  → Timestamp
# Col 3  → Consent
# Col 4  → Weekly Rent (AUD)
# Col 5  → Monthly Income (AUD)
# Col 6  → Sydney Area
# Col 7  → Weekly UberEats
# Col 8  → Trust Level          ← filled after feedback
# Col 9  → AI Usefulness        ← filled after feedback
# Col 10 → Resilience Score
# Col 11 → Skipped Meals
# Col 12 → Parental Support Y/N
# Col 13 → Monthly Remittance
# Col 14 → Parental Support Amt
# Col 15 → Emergency Savings
# Col 16 → Weekly Transport
# Col 17 → Financial Literacy
# Col 18 → Months in Sydney
# Col 19 → Behavioural Intent   ← filled after feedback

st.set_page_config(page_title="Resilience Lab AI", page_icon="🛡️", layout="centered")

# ──────────────────────────────────────────────
# COLOUR PALETTE  (warm amber-gold on deep navy)
# ──────────────────────────────────────────────
COLORS = ["#f59e0b", "#e879f9", "#67e8f9", "#4ade80", "#fb7185", "#a78bfa"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

.stApp { background: #080c18; color: #e2e8f0; }
#MainMenu, footer, header { visibility: hidden; }

.stApp::before {
    content: '';
    display: block;
    height: 3px;
    background: linear-gradient(90deg, #f59e0b, #e879f9, #67e8f9);
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
}

.top-badge {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem; color: #f59e0b;
    letter-spacing: 0.22em; text-transform: uppercase;
    border: 1px solid #f59e0b44;
    background: #f59e0b11;
    display: inline-block;
    padding: 5px 14px; border-radius: 3px; margin-bottom: 1.2rem;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3rem; font-weight: 700;
    background: linear-gradient(135deg, #f59e0b 0%, #e879f9 60%, #67e8f9 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.15; margin-bottom: 0.6rem;
}
.hero-sub {
    font-size: 1rem; color: #7c93b8;
    margin-bottom: 2rem; font-weight: 300; line-height: 1.6;
}

.card {
    background: #0f1629;
    border: 1px solid #1e2d4a;
    border-radius: 14px; padding: 22px 24px; margin-bottom: 1rem;
}

.metric-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 14px; margin: 1.5rem 0;
}
.metric-card {
    background: #0f1629;
    border: 1px solid #1e2d4a;
    border-radius: 12px; padding: 22px 14px;
    text-align: center; position: relative; overflow: hidden;
}
.metric-card::after {
    content: ''; position: absolute;
    bottom: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #f59e0b, #e879f9);
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 2.1rem; font-weight: 700;
    color: #f59e0b; display: block; line-height: 1;
}
.metric-label {
    font-size: 0.68rem; color: #4a6080;
    text-transform: uppercase; letter-spacing: 0.12em; margin-top: 8px;
}

.analysis-box {
    background: linear-gradient(135deg, #0c1524, #0f1d35);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #f59e0b;
    border-radius: 12px; padding: 22px 26px;
    margin: 1.5rem 0; line-height: 1.85;
    color: #9ab3cc; font-size: 0.93rem;
}
.analysis-box b { color: #e2e8f0; }
.highlight      { color: #f59e0b; font-family: 'Space Mono', monospace; font-weight: 700; }
.highlight-pink { color: #e879f9; font-family: 'Space Mono', monospace; font-weight: 700; }
.highlight-cyan { color: #67e8f9; font-family: 'Space Mono', monospace; font-weight: 700; }

.pid-chip {
    font-family: 'Space Mono', monospace;
    background: #0f1629; border: 1px solid #1e2d4a;
    border-radius: 6px; padding: 7px 16px;
    font-size: 0.75rem; color: #f59e0b;
    display: inline-block; margin-bottom: 1.5rem; letter-spacing: 0.08em;
}

.step-bar { display: flex; gap: 6px; margin-bottom: 2.2rem; }
.step        { flex: 1; height: 3px; border-radius: 2px; background: #1e2d4a; }
.step.done   { background: #f59e0b; }
.step.active { background: linear-gradient(90deg, #f59e0b, #e879f9); }

.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem; color: #3a5070;
    text-transform: uppercase; letter-spacing: 0.18em;
    margin: 1.8rem 0 0.8rem 0;
    border-bottom: 1px solid #1e2d4a; padding-bottom: 8px;
}

.success-id {
    font-family: 'Space Mono', monospace;
    font-size: 1.3rem; color: #f59e0b;
    background: #0f1629; border: 1px solid #f59e0b33;
    border-radius: 10px; padding: 18px 24px;
    text-align: center; margin: 1.5rem 0; letter-spacing: 0.06em;
}

.insight-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; margin: 1rem 0; }
.insight-card {
    background: #0f1629; border: 1px solid #1e2d4a;
    border-radius: 10px; padding: 16px 18px;
}
.insight-card .i-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem; color: #3a5070;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;
}
.insight-card .i-value { font-family: 'Space Mono', monospace; font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.insight-card .i-sub   { font-size: 0.76rem; color: #4a6080; margin-top: 4px; }

.formula-box {
    background: #080c18; border: 1px solid #1e2d4a;
    border-radius: 10px; padding: 16px 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem; color: #7c93b8;
    margin: 0.75rem 0; line-height: 2;
}
.formula-box span.f1 { color: #f59e0b; }
.formula-box span.f2 { color: #e879f9; }
.formula-box span.f3 { color: #67e8f9; }

.bench-row   { margin: 12px 0; }
.bench-label { font-size: 0.8rem; color: #7c93b8; margin-bottom: 5px; }
.bench-track { background: #1e2d4a; border-radius: 4px; height: 8px; width: 100%; position: relative; }
.bench-fill  { height: 8px; border-radius: 4px; }
.bench-marker{ position: absolute; top: -4px; width: 3px; height: 16px; background: #f59e0b; border-radius: 2px; }

.rec-card {
    background: #0f1629; border: 1px solid #1e2d4a;
    border-left: 3px solid #f59e0b;
    border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;
}
.rec-title { font-family: 'Space Mono', monospace; font-size: 0.72rem; color: #f59e0b; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }
.rec-body  { font-size: 0.88rem; color: #9ab3cc; line-height: 1.7; }

.stButton > button {
    background: linear-gradient(135deg, #b45309, #d97706) !important;
    color: #080c18 !important; border: none !important; border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important; font-size: 0.8rem !important;
    letter-spacing: 0.06em !important; height: 3rem !important;
    width: 100% !important; font-weight: 700 !important;
}
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #b45309, #d97706) !important;
    color: #080c18 !important; border: none !important; border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important; font-size: 0.8rem !important;
    height: 3rem !important; width: 100% !important; font-weight: 700 !important;
}
hr { border-color: #1e2d4a !important; margin: 1.8rem 0 !important; }

.stTabs [data-baseweb="tab-list"] {
    background: #0f1629 !important; border-radius: 10px;
    padding: 4px; gap: 4px; border: 1px solid #1e2d4a;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #4a6080 !important;
    border-radius: 7px !important;
    font-family: 'Space Mono', monospace !important; font-size: 0.72rem !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #b45309, #d97706) !important; color: #080c18 !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# CHART LAYOUT DEFAULTS
# ──────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#7c93b8", family="Space Mono"),
    margin=dict(t=30, b=30, l=10, r=10),
)

# ──────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────
def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception as e:
        st.error(f"❌ Sheet connection failed: {e}")
        return None


def append_and_get_row(sheet, row_data):
    response = sheet.append_row(
        row_data,
        value_input_option="USER_ENTERED",
        insert_data_option="INSERT_ROWS"   # ← forces a brand new row every time
    )
    updated_range = response["updates"]["updatedRange"]
    match = re.search(r':.*?(\d+)$', updated_range)
    return int(match.group(1)) if match else None


# ──────────────────────────────────────────────
# AI ENGINE
# ──────────────────────────────────────────────
def run_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    exp_vals = {
        "Housing":    float(data['rent'])  * 4.33,
        "Groceries":  float(data['groc'])  * 4.33,
        "Lifestyle":  float(data['uber'])  * 4.33,
        "Transport":  float(data['trans']) * 4.33,
        "Bills":      float(data['bills']),
        "Remittance": float(data['remit']),
    }
    m_exp   = sum(exp_vals.values())
    surplus = m_inc - m_exp
    savings = float(data['savings'])
    runway  = round(savings / m_exp, 1) if m_exp > 0 else 0.0

    z    = (surplus / (m_exp if m_exp > 0 else 1)) * 5
    prob = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 \
           else round(max(5.0, 25.0 + (surplus / 500)), 1)

    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = (
        (surplus / m_inc) * 40
        + lit_map[data['lit']] * 0.2
        + (20 if data['p_supp'] == "Yes" else 0)
        + 30
    )
    if data['meals'] == "Yes":
        score -= 25

    rent_pct  = round((exp_vals["Housing"]   / m_inc) * 100, 1)
    uber_pct  = round((exp_vals["Lifestyle"] / m_inc) * 100, 1)
    groc_pct  = round((exp_vals["Groceries"] / m_inc) * 100, 1)
    trans_pct = round((exp_vals["Transport"] / m_inc) * 100, 1)
    save_rate = round((max(surplus, 0) / m_inc) * 100, 1)

    flags = []
    if rent_pct > 40:
        flags.append(f"⚠️ Housing consumes <b>{rent_pct}%</b> of income — above the recommended 30% threshold.")
    if uber_pct > 15:
        flags.append(f"⚠️ Discretionary lifestyle spend at <b>{uber_pct}%</b> — consider reducing to improve runway.")
    if runway < 2:
        flags.append("🔴 Financial runway critically low — under 2 months of savings coverage.")
    if data['meals'] == "Yes":
        flags.append("🔴 Meal-skipping detected — signals acute financial stress.")
    if surplus < 0:
        flags.append(f"🔴 Monthly deficit of <b>${abs(round(surplus, 0))}</b> — expenditure exceeds income.")

    score_components = {
        "Surplus Ratio (×40)":       round((surplus / m_inc) * 40, 1),
        "Fin. Literacy (×0.2)":      round(lit_map[data['lit']] * 0.2, 1),
        "Family Support (+20)":       20 if data['p_supp'] == "Yes" else 0,
        "Base Score (+30)":           30,
        "Meal-Skip Penalty (−25)":   -25 if data['meals'] == "Yes" else 0,
    }

    return {
        "surplus":          round(surplus, 2),
        "m_inc":            round(m_inc, 2),
        "m_exp":            round(m_exp, 2),
        "score":            int(min(max(score, 5), 100)),
        "prob":             min(prob, 100.0),
        "runway":           runway,
        "rent_pct":         rent_pct,
        "uber_pct":         uber_pct,
        "groc_pct":         groc_pct,
        "trans_pct":        trans_pct,
        "save_rate":        save_rate,
        "exp_breakdown":    exp_vals,
        "flags":            flags,
        "score_components": score_components,
        "lit_score":        lit_map[data['lit']],
    }


# ──────────────────────────────────────────────
# SESSION INIT
# ──────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = "home"

# ══════════════════════════════════════════════
# FINISHED
# ══════════════════════════════════════════════
if st.session_state.step == "finished":
    st.balloons()
    st.markdown('<div class="top-badge">Research Complete</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Data Secured ✓</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Your response has been recorded. Thank you for contributing to this research.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="success-id">Participant ID: {st.session_state.get("last_id","—")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="analysis-box">You may safely close this window. Your data will be used solely for academic research on financial resilience among international students in Sydney.</div>', unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════
if st.session_state.step == "home":
    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="top-badge">Sydney · Academic Research · 2025</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br>Lab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">The impact of predictive AI analytics on the financial resilience of international students — focusing on discretionary spending behaviour.</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <div class="section-header">What to expect</div>
        Takes approximately <b>3 minutes</b>. You will provide anonymised financial data and receive
        a personalised AI resilience report with charts and breakdowns.
        All data is encrypted and used for academic purposes only.
    </div>""", unsafe_allow_html=True)

    consent = st.checkbox("I voluntarily consent to participate in this research study and understand my data will be anonymised.")
    if consent:
        if st.button("▶  INITIALISE SESSION"):
            st.session_state.participant_id = f"RES-{random.randint(100000, 999999)}"
            st.session_state.step = "inputs"
            st.rerun()

# ══════════════════════════════════════════════
# INPUTS
# ══════════════════════════════════════════════
elif st.session_state.step == "inputs":
    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step active"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Financial<br>Profile</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">All figures are monthly unless stated otherwise.</div>', unsafe_allow_html=True)

    with st.form("input_form"):
        st.markdown('<div class="section-header">Location</div>', unsafe_allow_html=True)
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield",
                           "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
        addr = st.selectbox("Suburb of Residence", suburbs)
        custom_sub = st.text_input("If 'Other', please specify:", placeholder="e.g. Chatswood")
        final_addr = custom_sub.strip() if addr == "Other" else addr

        st.markdown('<div class="section-header">Income</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: inc    = st.number_input("Monthly Income (AUD $)", min_value=0, max_value=15000, value=3200, step=50)
        with col2: p_supp = st.radio("Receiving Family Support?", ["No", "Yes"], horizontal=True)
        p_amt = st.number_input("Family Support Amount ($/mo) — enter 0 if none", min_value=0, max_value=5000, value=0, step=50)

        st.markdown('<div class="section-header">Core Weekly Expenses</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: rent  = st.number_input("Rent ($/wk)",      min_value=0, max_value=2000, value=450, step=10)
        with col2: groc  = st.number_input("Groceries ($/wk)", min_value=0, max_value=500,  value=140, step=10)
        with col3: trans = st.number_input("Transport ($/wk)", min_value=0, max_value=300,  value=45,  step=5)

        st.markdown('<div class="section-header">Discretionary Spending</div>', unsafe_allow_html=True)
        uber = st.slider("Uber Eats / Eating Out / Lifestyle ($/wk)", min_value=0, max_value=800, value=120, step=10)

        st.markdown('<div class="section-header">Financial Position</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: bills   = st.number_input("Fixed Bills ($/mo)",    min_value=0, max_value=1000,   value=150,  step=10)
        with col2: remit   = st.number_input("Remittance ($/mo)",     min_value=0, max_value=3000,   value=0,    step=50)
        with col3: savings = st.number_input("Emergency Savings ($)", min_value=0, max_value=100000, value=2000, step=100)

        st.markdown('<div class="section-header">Background</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: lit    = st.select_slider("Financial Literacy Level", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        with col2: months = st.number_input("Months Living in Sydney", min_value=1, max_value=120, value=12)

        meals = st.radio("Have you skipped meals due to lack of money in the past month?", ["No", "Yes"], horizontal=True)
   st.markdown("---")
        submitted = st.form_submit_button("⚡  GENERATE AI REPORT")
elif st.session_state.step == "inputs":
    st.markdown('<div class="step-bar">...</div>', unsafe_allow_html=True)
    # ... all your inputs code ...

    with st.form("input_form"):
        # ... all form fields ...
        st.markdown("---")
        submitted = st.form_submit_button("⚡  GENERATE AI REPORT")

    if submitted and not st.session_state.get("data_saved"):  # ← 4 spaces
        if addr == "Other" and not final_addr:                 # ← 8 spaces
            st.warning("Please specify your suburb.")
        else:                                                  # ← 8 spaces
            data = {
                "income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit,
                "rent": rent, "uber": uber, "groc": groc, "trans": trans,
                "bills": bills, "meals": meals, "addr": final_addr,
                "savings": savings, "lit": lit, "months": months,
            }
            res = run_model(data)
            st.session_state.data = data
            st.session_state.res  = res
            with st.spinner("Saving to research database..."):
                sheet = connect_to_sheet()
                if sheet:
                    sydney_time = datetime.utcnow() + timedelta(hours=11)
                    row = [
                        st.session_state.participant_id,
                        sydney_time.strftime("%d %b %Y  %I:%M %p"),
                        "Yes",
                        rent, inc, final_addr, uber,
                        "", "",
                        res['score'], meals, p_supp, remit,
                        p_amt, savings, trans, lit, months,
                        "",
                    ]
                    try:
                        st.session_state.target_row = append_and_get_row(sheet, row)
                        st.session_state.data_saved = True
                    except Exception as e:
                        st.error(f"❌ Failed to save: {e}")
                        st.stop()
                else:
                    st.stop()
            st.session_state.step = "results"
            st.rerun()
# ══════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════
elif st.session_state.step == "results":
    ai   = st.session_state.res
    data = st.session_state.data

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step active"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br>Dashboard</div>', unsafe_allow_html=True)

    surplus_display = f"+${ai['surplus']}" if ai['surplus'] >= 0 else f"-${abs(ai['surplus'])}"

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <span class="metric-value">{ai['score']}</span>
            <div class="metric-label">Resilience Score</div>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color:#e879f9">{ai['runway']}</span>
            <div class="metric-label">Runway (months)</div>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color:#67e8f9">{ai['prob']}%</span>
            <div class="metric-label">Stability Prob.</div>
        </div>
    </div>""", unsafe_allow_html=True)
    flags_html = "".join(
        f"<li style='margin:7px 0'>{f}</li>" for f in ai['flags']
    ) if ai['flags'] else "<li>✅ No critical stress indicators detected.</li>"
    st.markdown(f"""
    <div class="analysis-box">
        <b>AI Analysis — {data['addr']}</b><br><br>
        Housing costs represent <span class="highlight">{ai['rent_pct']}%</span> of total income
        and discretionary spending accounts for
        <span class="highlight-pink">{ai['uber_pct']}%</span>.
        Monthly surplus is <span class="highlight">{surplus_display}</span> with a financial runway
        of <span class="highlight-cyan">{ai['runway']} months</span>.<br><br>
        <b>Key Indicators:</b>
        <ul style="margin:10px 0 0 0; padding-left:20px">{flags_html}</ul>
    </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊  Spending",
        "📈  Benchmarks",
        "🔬  Score Logic",
        "💡  Recommendations",
    ])

    # ── TAB 1: Spending ────────────────────────
    with tab1:
        st.markdown('<div class="section-header">Monthly Expense Distribution</div>', unsafe_allow_html=True)
        fig_pie = px.pie(
            values=list(ai['exp_breakdown'].values()),
            names=list(ai['exp_breakdown'].keys()),
            hole=0.58, color_discrete_sequence=COLORS,
        )
        fig_pie.update_layout(**CHART_LAYOUT, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)))
        fig_pie.update_traces(textfont_color="#e2e8f0", marker=dict(line=dict(color="#080c18", width=2)))
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown('<div class="section-header">Income vs Total Expenses</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Total Income", "Total Expenses", "Monthly Surplus"],
            y=[ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)],
            marker_color=["#4ade80", "#f87171", "#f59e0b"],
            marker_line=dict(color="#080c18", width=2),
            text=[f"${v:,.0f}" for v in [ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)]],
            textposition="outside", textfont=dict(color="#e2e8f0", size=13),
        ))
        fig_bar.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(showgrid=False, showticklabels=False),
            xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#7c93b8")),
            showlegend=False, height=320,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown('<div class="section-header">Each Category as % of Income</div>', unsafe_allow_html=True)
        categories = list(ai['exp_breakdown'].keys())
        pct_vals   = [round(v / ai['m_inc'] * 100, 1) for v in ai['exp_breakdown'].values()]
        fig_h = go.Figure(go.Bar(
            x=pct_vals, y=categories, orientation='h',
            marker=dict(color=COLORS[:len(categories)], line=dict(color="#080c18", width=2)),
            text=[f"{p}%" for p in pct_vals],
            textposition="outside", textfont=dict(color="#e2e8f0"),
        ))
        fig_h.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#7c93b8")),
            showlegend=False, height=300,
        )
        st.plotly_chart(fig_h, use_container_width=True)

    # ── TAB 2: Benchmarks ──────────────────────
    with tab2:
        st.markdown('<div class="section-header">Your Spending vs Sydney Benchmarks</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="analysis-box" style="font-size:0.85rem">
        Based on the <b>50/30/20 rule</b> adapted for Sydney international students.
        The <span style="color:#f59e0b;font-weight:700">amber marker</span> shows your position;
        the shaded bar is the recommended safe range.
        </div>""", unsafe_allow_html=True)

        benchmarks = [
            ("Housing % of Income",       ai['rent_pct'],  30, 40, "%"),
            ("Discretionary % of Income", ai['uber_pct'],  10, 20, "%"),
            ("Groceries % of Income",     ai['groc_pct'],  10, 18, "%"),
            ("Transport % of Income",     ai['trans_pct'],  5, 12, "%"),
            ("Savings Rate",              ai['save_rate'],  20, 30, "%"),
        ]
        for label, val, rec_lo, rec_hi, unit in benchmarks:
            color = "#4ade80" if rec_lo <= val <= rec_hi else ("#f59e0b" if val < rec_lo else "#f87171")
            pct_w = min(val / 50 * 100, 100)
            st.markdown(f"""
            <div class="bench-row">
                <div class="bench-label">{label} &nbsp;
                    <span style="font-family:'Space Mono';color:{color};font-weight:700">{val}{unit}</span>
                    <span style="font-size:0.7rem;color:#3a5070"> · recommended {rec_lo}–{rec_hi}{unit}</span>
                </div>
                <div class="bench-track">
                    <div class="bench-fill" style="width:{pct_w:.0f}%;background:{color}55"></div>
                    <div class="bench-marker" style="left:{pct_w:.0f}%"></div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Spending Radar</div>', unsafe_allow_html=True)
        radar_cats = ["Housing", "Groceries", "Lifestyle", "Transport", "Bills", "Remittance"]
        radar_vals = [
            ai['rent_pct'], ai['groc_pct'], ai['uber_pct'], ai['trans_pct'],
            round(float(data['bills']) / ai['m_inc'] * 100, 1),
            round(float(data['remit']) / ai['m_inc'] * 100, 1),
        ]
        bench_vals = [30, 14, 15, 8, 5, 5]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=bench_vals + [bench_vals[0]], theta=radar_cats + [radar_cats[0]],
            fill='toself', name='Benchmark',
            line=dict(color='#4ade80', dash='dash', width=1.5),
            fillcolor='rgba(74,222,128,0.06)',
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=radar_vals + [radar_vals[0]], theta=radar_cats + [radar_cats[0]],
            fill='toself', name='Your Profile',
            line=dict(color='#f59e0b', width=2),
            fillcolor='rgba(245,158,11,0.12)',
        ))
        fig_radar.update_layout(
            **CHART_LAYOUT,
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0, 50], color='#3a5070', gridcolor='#1e2d4a'),
                angularaxis=dict(color='#7c93b8', gridcolor='#1e2d4a'),
            ),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
            height=400,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── TAB 3: Score Logic ─────────────────────
    with tab3:
        st.markdown('<div class="section-header">How Your Resilience Score Was Calculated</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="formula-box">
            Score = <span class="f1">(Surplus ÷ Income) × 40</span><br>
                  + <span class="f2">Financial Literacy × 0.2</span><br>
                  + <span class="f3">Family Support Bonus  (+20 if Yes)</span><br>
                  + <span class="f1">Base Score  (+30)</span><br>
                  − <span class="f2">Meal-Skip Penalty  (−25 if Yes)</span><br>
            → Clamped between <span class="f3">5</span> and <span class="f3">100</span>
        </div>""", unsafe_allow_html=True)

        components = ai['score_components']
        values     = list(components.values())
        running    = sum(values)
        measures   = ["relative"] * len(values) + ["total"]

        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=measures,
            x=list(components.keys()) + ["Final Score"],
            y=values + [running],
            connector=dict(line=dict(color="#1e2d4a", width=1)),
            increasing=dict(marker_color="#4ade80"),
            decreasing=dict(marker_color="#f87171"),
            totals=dict(marker_color="#f59e0b"),
            text=[f"{v:+.1f}" for v in values] + [f"{running:.0f}"],
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=11),
        ))
        fig_wf.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(showgrid=False, range=[min(0, min(values)) - 10, max(running, 100) + 20]),
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#7c93b8")),
            showlegend=False, height=400,
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        score_color = "#4ade80" if ai['score'] >= 60 else ("#f59e0b" if ai['score'] >= 35 else "#f87171")
        score_label = "Strong" if ai['score'] >= 60 else ("Moderate" if ai['score'] >= 35 else "Vulnerable")
        st.markdown(f"""
        <div class="insight-grid">
            <div class="insight-card">
                <div class="i-label">Final Score</div>
                <div class="i-value" style="color:{score_color}">{ai['score']}/100</div>
                <div class="i-sub">Resilience: {score_label}</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Literacy Contribution</div>
                <div class="i-value" style="color:#e879f9">{ai['lit_score']}</div>
                <div class="i-sub">Level: {data['lit']}</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Monthly Surplus</div>
                <div class="i-value" style="color:{'#4ade80' if ai['surplus']>=0 else '#f87171'}">{surplus_display}</div>
                <div class="i-sub">Income − All Expenses</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Stability Probability</div>
                <div class="i-value" style="color:#67e8f9">{ai['prob']}%</div>
                <div class="i-sub">Logistic model on surplus ratio</div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── TAB 4: Recommendations ─────────────────
    with tab4:
        st.markdown('<div class="section-header">AI-Generated Recommendations</div>', unsafe_allow_html=True)

        recs = []
        if ai['rent_pct'] > 40:
            recs.append(("🏠 Housing Cost", f"Your rent is {ai['rent_pct']}% of income. Consider shared accommodation in Auburn, Hurstville, or Parramatta — rents are 15–25% lower than the CBD."))
        if ai['uber_pct'] > 15:
            saving = round(float(data['uber']) * 4.33 * 0.4, 0)
            recs.append(("🍔 Discretionary Spend", f"Cutting Uber/lifestyle by 40% frees ~${saving}/mo. Cook at home 4–5 days/week and use Opal card instead of rideshare."))
        if ai['runway'] < 3:
            recs.append(("💰 Emergency Fund", f"Only {ai['runway']} months of runway. Aim for 3 months' cover — saving $50–100/week accelerates this significantly."))
        if float(data['remit']) > ai['m_inc'] * 0.15:
            recs.append(("💸 Remittance", "Remittances exceed 15% of income. Try Wise or Remitly for lower fees and batch transfers monthly."))
        if data['lit'] == "Novice":
            recs.append(("📚 Financial Literacy", "Free resources: MoneySmart (ASIC), Student Edge, and your university's financial counselling service."))
        if data['meals'] == "Yes":
            recs.append(("🍱 Food Security", "Meal-skipping is a critical stress signal. Access free meals at your university's student hub, or register with OzHarvest and Foodbank NSW."))
        if ai['surplus'] < 0:
            recs.append(("⚡ Urgent: Deficit", f"Spending ${abs(ai['surplus'])}/mo more than you earn. Contact your university's financial hardship office immediately."))
        if not recs:
            recs.append(("✅ On Track", "No critical stress points detected. Maintain your surplus and consider increasing savings toward 20%."))

        for title, body in recs:
            st.markdown(f"""
            <div class="rec-card">
                <div class="rec-title">{title}</div>
                <div class="rec-body">{body}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">12-Month Savings Projection</div>', unsafe_allow_html=True)
        months_proj = list(range(0, 13))
        current_sav = float(data['savings'])
        monthly_add = max(ai['surplus'], 0)
        proj_base   = [current_sav + monthly_add * m for m in months_proj]
        proj_opt    = [current_sav + (monthly_add * 1.2) * m for m in months_proj]

        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=months_proj, y=proj_base, name="Current trajectory",
            line=dict(color="#f59e0b", width=2.5),
            fill='tozeroy', fillcolor='rgba(245,158,11,0.06)',
        ))
        fig_proj.add_trace(go.Scatter(
            x=months_proj, y=proj_opt, name="If 20% more saved",
            line=dict(color="#4ade80", width=2, dash='dash'),
        ))
        fig_proj.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(title="Month", showgrid=False, color="#3a5070"),
            yaxis=dict(title="Savings (AUD $)", showgrid=False, color="#3a5070"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
            height=320,
        )
        st.plotly_chart(fig_proj, use_container_width=True)

    # ══════════════════════════════════════════
    # FEEDBACK FORM
    # ══════════════════════════════════════════
    st.markdown("---")
    st.markdown('<div class="section-header">Research Evaluation</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="font-size:0.9rem">Please evaluate the AI report before submitting your final response.</div>', unsafe_allow_html=True)

    with st.form("feedback_form"):
        col1, col2 = st.columns(2)
        with col1: trust  = st.select_slider("How much do you trust the AI analysis?", options=["Low","Neutral","High"], value="Neutral")
        with col2: useful = st.select_slider("Was this report enlightening?", options=["No","Neutral","Yes"], value="Neutral")

        intent = st.radio(
            "After seeing this report, what is your most likely next action?",
            ["Reduce discretionary spending", "Search for cheaper housing",
             "Seek additional income", "No change planned"],
        )
        st.markdown("---")
        lock = st.form_submit_button("🔒  SUBMIT & LOCK RESPONSE")

    if lock:
        with st.spinner("Locking your response..."):
            sheet = connect_to_sheet()
            if sheet and st.session_state.get("target_row"):
                try:
                    row_idx = st.session_state.target_row
                    # Col 8 = Trust Level, Col 9 = AI Usefulness
                    sheet.update([[trust, useful]], f"H{row_idx}:I{row_idx}")
                    # Col 19 = Behavioural Intent
                    sheet.update_cell(row_idx, 19, intent)
                    st.session_state.last_id = st.session_state.participant_id
                    st.session_state.step = "finished"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save feedback: {e}")
            elif not st.session_state.get("target_row"):
                st.error("⚠️ Row reference lost — please restart the survey.")
            else:
                st.error("❌ Could not connect to sheet.")





