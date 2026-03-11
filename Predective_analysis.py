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

# ── Column map (1-indexed) ──────────────────────────────────────────────────
# 1   Unique_ID
# 2   Timestamp
# 3   Consent
# 4   Weekly Rent (AUD)
# 5   Monthly Income (AUD)
# 6   Sydney Area
# 7   Weekly Discretionary (AUD)
# ── PRE-EXPOSURE BASELINE (collected BEFORE financial inputs & AI report) ──
# 8   PRE_FinancialStress        (1–5 Likert)
# 9   PRE_SpendingConfidence     (1–5 Likert)
# 10  PRE_AITrustBaseline        (1–5 Likert)
# ── FINANCIAL / MODEL OUTPUTS ──────────────────────────────────────────────
# 11  Resilience_Score
# 12  Skipped_Meals
# 13  Parental_Support_YN
# 14  Monthly_Remittance
# 15  Parental_Support_Amt
# 16  Emergency_Savings
# 17  Weekly_Transport
# 18  Financial_Literacy
# 19  Months_in_Sydney
# ── POST-EXPOSURE SCALES (collected AFTER seeing AI report) ────────────────
# McKnight et al. (2011) Trust in AI — 4 items, 1–5 Likert
# 20  POST_Trust_Competence
# 21  POST_Trust_Benevolence
# 22  POST_Trust_Integrity
# 23  POST_Trust_Intention
# Perceived Usefulness — PRIMARY DV, Davis (1989) adapted, 1–5 Likert
# 24  POST_PU_Understanding
# 25  POST_PU_Useful
# 26  POST_PU_DecisionAid
# Behavioural intent (categorical)
# 27  POST_BehaviouralIntent
# ───────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Resilience Lab AI", page_icon="🛡️", layout="centered")

COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4", "#4ade80", "#fb7185", "#f59e0b"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #06091a; color: #e2e8f0; }
#MainMenu, footer, header { visibility: hidden; }

.stApp::before {
    content: ''; display: block; height: 2px;
    background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
}

/* ── Widget labels ── */
label, div[data-testid="stWidgetLabel"] p, div[data-testid="stWidgetLabel"] {
    color: #94a3b8 !important; font-size: 0.87rem !important; font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Inputs ── */
input[type="number"], input[type="text"], textarea,
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: #0d1530 !important; color: #f1f5f9 !important;
    border: 1px solid #1e3054 !important; border-radius: 6px !important;
    font-size: 0.9rem !important; font-family: 'DM Sans', sans-serif !important;
}
input:focus, textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important; outline: none !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div, div[data-baseweb="select"] > div {
    background: #0d1530 !important; border: 1px solid #1e3054 !important;
    border-radius: 6px !important; color: #f1f5f9 !important;
}
div[data-baseweb="select"] span, div[data-baseweb="select"] div { color: #f1f5f9 !important; }
ul[data-baseweb="menu"], div[data-baseweb="popover"] ul {
    background: #0f1d40 !important; border: 1px solid #1e3054 !important; border-radius: 6px !important;
}
ul[data-baseweb="menu"] li { color: #e2e8f0 !important; background: transparent !important; }
ul[data-baseweb="menu"] li:hover { background: #1e3a6a !important; color: #fff !important; }

/* ── Radio ── */
.stRadio > div { gap: 8px !important; flex-wrap: wrap !important; }
.stRadio label {
    color: #94a3b8 !important; background: #0d1530 !important;
    border: 1px solid #1e3054 !important; border-radius: 6px !important;
    padding: 7px 14px !important; font-size: 0.83rem !important; cursor: pointer;
}
.stRadio label:hover { border-color: #3b82f6 !important; color: #e2e8f0 !important; }
.stRadio [aria-checked="true"] + label, .stRadio input:checked + div {
    border-color: #3b82f6 !important; background: #142154 !important; color: #fff !important;
}

/* ── Slider ── */
.stSlider > div > div > div > div { background: #3b82f6 !important; }
.stSlider [data-baseweb="slider"] > div:first-child { background: #1a2a4a !important; }
.stSlider p, .stSlider span { color: #94a3b8 !important; }

/* ── Number input spinners ── */
.stNumberInput button {
    background: #0d1530 !important; border-color: #1e3054 !important; color: #e2e8f0 !important;
}
.stNumberInput button:hover { background: #1e3054 !important; }

/* ── Checkbox ── */
.stCheckbox label { color: #94a3b8 !important; font-size: 0.88rem !important; }
.stCheckbox span  { border-color: #1e3054 !important; background: #0d1530 !important; }

/* ── Text ── */
.stApp p, .stMarkdown p { color: #94a3b8; line-height: 1.75; }
.stForm { background: transparent !important; border: none !important; }

/* ── Buttons ── */
.stButton > button, div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important;
    color: #fff !important; border: none !important; border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.77rem !important;
    letter-spacing: 0.05em !important; height: 3rem !important;
    width: 100% !important; font-weight: 500 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1530 !important; border-radius: 8px; padding: 4px; gap: 4px;
    border: 1px solid #1e3054;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #64748b !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.68rem !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important; color: #fff !important;
}

hr { border-color: #1a2a4a !important; margin: 1.6rem 0 !important; }

/* ── Custom components ── */
.top-badge {
    font-family: 'DM Mono', monospace; font-size: 0.62rem; color: #3b82f6;
    letter-spacing: 0.2em; text-transform: uppercase;
    border: 1px solid #1e3a6a; background: #0d1f40;
    display: inline-block; padding: 5px 14px; border-radius: 3px; margin-bottom: 1.2rem;
}
.hero-title {
    font-family: 'Syne', sans-serif; font-size: 2.8rem; font-weight: 800;
    background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 55%, #34d399 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.15; margin-bottom: 0.5rem;
}
.hero-sub {
    font-size: 0.95rem; color: #64748b; margin-bottom: 2rem;
    font-weight: 300; line-height: 1.7;
}
.card {
    background: #0b1428; border: 1px solid #1a2a4a;
    border-radius: 12px; padding: 20px 22px; margin-bottom: 1rem; color: #94a3b8;
}
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 1.4rem 0; }
.metric-card {
    background: #0b1428; border: 1px solid #1a2a4a;
    border-radius: 10px; padding: 20px 12px; text-align: center;
    position: relative; overflow: hidden;
}
.metric-card::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
}
.metric-value {
    font-family: 'DM Mono', monospace; font-size: 2rem; font-weight: 500;
    color: #60a5fa; display: block; line-height: 1;
}
.metric-label {
    font-size: 0.64rem; color: #475569; text-transform: uppercase;
    letter-spacing: 0.12em; margin-top: 8px;
}
.analysis-box {
    background: #090f22; border: 1px solid #1a2a4a; border-left: 3px solid #3b82f6;
    border-radius: 10px; padding: 20px 24px; margin: 1.4rem 0;
    line-height: 1.85; color: #94a3b8; font-size: 0.91rem;
}
.analysis-box b { color: #e2e8f0; }
.highlight      { color: #60a5fa; font-family: 'DM Mono', monospace; font-weight: 500; }
.highlight-pink { color: #a78bfa; font-family: 'DM Mono', monospace; font-weight: 500; }
.highlight-cyan { color: #34d399; font-family: 'DM Mono', monospace; font-weight: 500; }
.pid-chip {
    font-family: 'DM Mono', monospace; background: #0b1428; border: 1px solid #1a2a4a;
    border-radius: 5px; padding: 6px 14px; font-size: 0.72rem; color: #60a5fa;
    display: inline-block; margin-bottom: 1.4rem; letter-spacing: 0.08em;
}
.step-bar { display: flex; gap: 5px; margin-bottom: 2rem; }
.step        { flex: 1; height: 2px; border-radius: 2px; background: #1a2a4a; }
.step.done   { background: #3b82f6; }
.step.active { background: linear-gradient(90deg, #3b82f6, #8b5cf6); }
.section-header {
    font-family: 'DM Mono', monospace; font-size: 0.63rem; color: #475569;
    text-transform: uppercase; letter-spacing: 0.18em;
    margin: 1.6rem 0 0.8rem 0; border-bottom: 1px solid #1a2a4a; padding-bottom: 7px;
}
.success-id {
    font-family: 'DM Mono', monospace; font-size: 1.2rem; color: #60a5fa;
    background: #0b1428; border: 1px solid #1a2a4a; border-radius: 8px;
    padding: 16px 22px; text-align: center; margin: 1.4rem 0; letter-spacing: 0.06em;
}
.locked-box {
    background: #090f22; border: 1px solid #3b82f655; border-left: 3px solid #3b82f6;
    border-radius: 10px; padding: 22px 26px; margin: 1.5rem 0;
    line-height: 1.8; color: #94a3b8; font-size: 0.91rem; text-align: center;
}
.locked-box .lock-icon { font-size: 2.2rem; display: block; margin-bottom: 10px; }
.locked-box .lock-title {
    font-family: 'DM Mono', monospace; font-size: 1rem;
    color: #60a5fa; font-weight: 500; margin-bottom: 8px;
}
.insight-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; margin: 1rem 0; }
.insight-card { background: #0b1428; border: 1px solid #1a2a4a; border-radius: 8px; padding: 14px 16px; }
.insight-card .i-label {
    font-family: 'DM Mono', monospace; font-size: 0.62rem; color: #475569;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 5px;
}
.insight-card .i-value {
    font-family: 'DM Mono', monospace; font-size: 1.4rem; font-weight: 500; color: #f1f5f9;
}
.insight-card .i-sub { font-size: 0.74rem; color: #475569; margin-top: 3px; }
.formula-box {
    background: #06091a; border: 1px solid #1a2a4a; border-radius: 8px; padding: 15px 18px;
    font-family: 'DM Mono', monospace; font-size: 0.76rem; color: #94a3b8;
    margin: 0.75rem 0; line-height: 2;
}
.formula-box .f1 { color: #60a5fa; }
.formula-box .f2 { color: #a78bfa; }
.formula-box .f3 { color: #34d399; }
.formula-box .cite { color: #334155; font-size: 0.66rem; }
.bench-row   { margin: 12px 0; }
.bench-label { font-size: 0.8rem; color: #94a3b8; margin-bottom: 5px; }
.bench-track { background: #1a2a4a; border-radius: 3px; height: 7px; width: 100%; position: relative; }
.bench-fill  { height: 7px; border-radius: 3px; }
.bench-marker{ position: absolute; top: -4px; width: 2px; height: 15px; background: #60a5fa; border-radius: 2px; }
.rec-card {
    background: #0b1428; border: 1px solid #1a2a4a; border-left: 3px solid #3b82f6;
    border-radius: 8px; padding: 15px 18px; margin-bottom: 10px;
}
.rec-title {
    font-family: 'DM Mono', monospace; font-size: 0.66rem; color: #60a5fa;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 7px;
}
.rec-body { font-size: 0.86rem; color: #94a3b8; line-height: 1.7; }
.scale-block {
    background: #090f22; border: 1px solid #1a2a4a; border-radius: 10px;
    padding: 18px 20px; margin-bottom: 10px;
}
.scale-q { font-size: 0.92rem; color: #cbd5e1; font-weight: 500; margin-bottom: 3px; }
.scale-cite {
    font-family: 'DM Mono', monospace; font-size: 0.63rem; color: #334155;
    margin-bottom: 10px; display: block;
}
.scale-anchors {
    display: flex; justify-content: space-between;
    font-size: 0.67rem; color: #475569; margin-top: 2px;
    font-family: 'DM Mono', monospace;
}
.pre-notice {
    background: #090f22; border: 1px solid #1a2a4a; border-left: 3px solid #f59e0b;
    border-radius: 10px; padding: 16px 20px; margin-bottom: 1.4rem;
    font-size: 0.86rem; color: #94a3b8; line-height: 1.7;
}
.pre-notice b { color: #f59e0b; }
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#64748b", family="DM Mono"),
    margin=dict(t=30, b=30, l=10, r=10),
)

LIKERT_5 = ["1 — Strongly Disagree", "2 — Disagree", "3 — Neutral", "4 — Agree", "5 — Strongly Agree"]

def likert_val(s):
    """Extract integer from Likert label e.g. '4 — Agree' → 4"""
    return int(s.split("—")[0].strip())


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
        insert_data_option="INSERT_ROWS",
    )
    updated_range = response["updates"]["updatedRange"]
    match = re.search(r':.*?(\d+)$', updated_range)
    return int(match.group(1)) if match else None


def id_already_submitted(sheet, participant_id):
    try:
        col_a = sheet.col_values(1)
        return participant_id in col_a
    except Exception:
        return False


# ──────────────────────────────────────────────
# SCORING MODEL
# ──────────────────────────────────────────────
# Theoretical grounding:
#   C1 Surplus Ratio      — Carroll (1997) buffer stock / income adequacy
#   C2 Housing Stress     — AHURI (2023) 30% of income threshold for Australia
#   C3 Emergency Buffer   — Deaton (1991); recommended ≥3 months expenses
#   C4 Financial Literacy — Lusardi & Mitchell (2014) tripartite literacy scale
#   C5 Food Security      — Gundersen & Ziliak (2015) meal-skipping as
#                           indicator of acute financial hardship
#
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

    # Stability probability: logistic on surplus-to-expense ratio
    z    = (surplus / (m_exp if m_exp > 0 else 1)) * 5
    prob = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 \
           else round(max(5.0, 25.0 + (surplus / 500)), 1)

    # Lusardi & Mitchell (2014) literacy weights
    lit_map = {"Novice": 25, "Intermediate": 60, "Advanced": 90}
    lit_score = lit_map[data['lit']]

    # ── C1: Surplus Ratio (max 35 pts) — Carroll (1997)
    sir = surplus / m_inc if m_inc > 0 else -1.0
    c_surplus = max(0.0, min(35.0, (sir + 0.5) * 35))

    # ── C2: Housing Stress (max 25 pts) — AHURI (2023)
    rent_pct = (exp_vals["Housing"] / m_inc) * 100 if m_inc > 0 else 100
    if   rent_pct <= 25: c_housing = 25
    elif rent_pct <= 30: c_housing = 18
    elif rent_pct <= 40: c_housing = 8
    else:                c_housing = 0

    # ── C3: Emergency Buffer (max 20 pts) — Deaton (1991)
    if   runway >= 6: c_buffer = 20
    elif runway >= 3: c_buffer = 14
    elif runway >= 1: c_buffer = 6
    else:             c_buffer = 0

    # ── C4: Financial Literacy (max 10 pts) — Lusardi & Mitchell (2014)
    c_literacy = round(lit_score * 0.111, 1)   # 25→2.8, 60→6.7, 90→10.0

    # ── C5: Food Security (max 10 pts) — Gundersen & Ziliak (2015)
    c_food = 0 if data['meals'] == "Yes" else 10

    score = int(min(max(round(c_surplus + c_housing + c_buffer + c_literacy + c_food), 5), 100))

    # Derived ratios
    uber_pct  = round((exp_vals["Lifestyle"]  / m_inc) * 100, 1)
    groc_pct  = round((exp_vals["Groceries"]  / m_inc) * 100, 1)
    trans_pct = round((exp_vals["Transport"]  / m_inc) * 100, 1)
    remit_pct = round((exp_vals["Remittance"] / m_inc) * 100, 1)
    save_rate = round((max(surplus, 0) / m_inc) * 100, 1)

    # Risk flags with citation anchors
    flags = []
    if rent_pct > 30:
        flags.append(f"⚠️ Housing stress: <b>{rent_pct:.1f}%</b> of income — exceeds AHURI's 30% threshold.")
    if uber_pct > 15:
        flags.append(f"⚠️ Discretionary spend at <b>{uber_pct:.1f}%</b> — above the 15% recommended ceiling.")
    if runway < 3:
        flags.append(f"🔴 Emergency buffer: <b>{runway} months</b> — below the 3-month minimum (Deaton 1991).")
    if data['meals'] == "Yes":
        flags.append("🔴 Meal-skipping detected — indicator of acute financial hardship (Gundersen & Ziliak 2015).")
    if surplus < 0:
        flags.append(f"🔴 Monthly deficit: <b>${abs(round(surplus)):,}</b> — expenditure exceeds total income.")
    if remit_pct > 15:
        flags.append(f"⚠️ Remittance burden at <b>{remit_pct:.1f}%</b> — World Bank recommends below 15%.")

    score_components = {
        "Surplus Ratio":    round(c_surplus,  1),
        "Housing Stress":   round(c_housing,  1),
        "Emerg. Buffer":    round(c_buffer,   1),
        "Fin. Literacy":    round(c_literacy, 1),
        "Food Security":    c_food,
    }

    return {
        "surplus": round(surplus, 2), "m_inc": round(m_inc, 2), "m_exp": round(m_exp, 2),
        "score": score, "prob": min(prob, 100.0), "runway": runway,
        "rent_pct": rent_pct, "uber_pct": uber_pct, "groc_pct": groc_pct,
        "trans_pct": trans_pct, "remit_pct": remit_pct, "save_rate": save_rate,
        "exp_breakdown": exp_vals, "flags": flags,
        "score_components": score_components, "lit_score": lit_score,
    }


# ──────────────────────────────────────────────
# SESSION STATE INIT
# ──────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step           = "home"
    st.session_state.data_saved     = False
    st.session_state.participant_id = f"RES-{random.randint(100000, 999999)}"


# ══════════════════════════════════════════════
# STEP: FINISHED
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
# STEP: HOME
# ══════════════════════════════════════════════
if st.session_state.step == "home":
    # 4-segment progress bar: Consent | Pre-Survey | Financial Profile | Dashboard + Post
    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="top-badge">Sydney · Academic Research · 2025</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br>Lab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Examining how AI-generated financial analytics influence perceived usefulness and financial resilience among international students in Sydney.</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <div class="section-header">What to expect</div>
        Takes approximately <b>4–5 minutes</b> and has four short stages:<br><br>
        <b>1.</b> A brief pre-survey (your baseline views) &nbsp;·&nbsp;
        <b>2.</b> Your anonymised financial profile &nbsp;·&nbsp;
        <b>3.</b> Your personalised AI resilience report &nbsp;·&nbsp;
        <b>4.</b> A short evaluation of the AI report<br><br>
        All responses are anonymised and used for academic purposes only.
    </div>""", unsafe_allow_html=True)

    consent = st.checkbox("I voluntarily consent to participate in this research study and understand my data will be anonymised.")
    if consent:
        if st.button("▶  BEGIN SURVEY"):
            st.session_state.step = "pre_survey"
            st.rerun()


# ══════════════════════════════════════════════
# STEP: PRE-SURVEY  (baseline — before AI exposure)
# ══════════════════════════════════════════════
elif st.session_state.step == "pre_survey":
    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step active"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Pre-Survey</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Answer based on how you feel right now — before seeing any AI-generated analysis.</div>', unsafe_allow_html=True)

    st.markdown('<div class="pre-notice"><b>Important:</b> These three questions capture your baseline views before you receive the AI report. Please answer honestly based on your current feelings.</div>', unsafe_allow_html=True)

    with st.form("pre_form"):
        st.markdown('<div class="section-header">Baseline Measures  <span style="color:#334155;font-size:0.6rem">1 = Strongly Disagree · 5 = Strongly Agree</span></div>', unsafe_allow_html=True)

        # PRE 1 — Financial Stress
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">I feel financially stressed as an international student living in Sydney.</div>
            <span class="scale-cite">Financial stress baseline — adapted from Norvilitis et al. (2006)</span>
        </div>""", unsafe_allow_html=True)
        pre_stress = st.radio("pre1", LIKERT_5, horizontal=True, key="pre_stress", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # PRE 2 — Spending Confidence
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">I am confident in my ability to manage my day-to-day spending.</div>
            <span class="scale-cite">Financial self-efficacy baseline — adapted from Lown (2011)</span>
        </div>""", unsafe_allow_html=True)
        pre_confidence = st.radio("pre2", LIKERT_5, horizontal=True, key="pre_confidence", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # PRE 3 — Baseline AI Trust
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">I trust AI-generated tools to provide useful guidance on financial matters.</div>
            <span class="scale-cite">Prior AI trust baseline — McKnight et al. (2011)</span>
        </div>""", unsafe_allow_html=True)
        pre_ai_trust = st.radio("pre3", LIKERT_5, horizontal=True, key="pre_ai_trust", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        next_btn = st.form_submit_button("NEXT  →  Financial Profile")

    if next_btn:
        st.session_state.pre = {
            "stress":     likert_val(pre_stress),
            "confidence": likert_val(pre_confidence),
            "ai_trust":   likert_val(pre_ai_trust),
        }
        st.session_state.step = "inputs"
        st.rerun()


# ══════════════════════════════════════════════
# STEP: FINANCIAL INPUTS
# ══════════════════════════════════════════════
elif st.session_state.step == "inputs":

    if st.session_state.data_saved:
        st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step active"></div></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="locked-box">
            <span class="lock-icon">🔒</span>
            <div class="lock-title">Response Already Recorded</div>
            Participant <b style="color:#60a5fa">{st.session_state.participant_id}</b>
            has already submitted.<br><br>
            Each participant may only submit once. Please pass the device to the next participant.
        </div>""", unsafe_allow_html=True)
        if st.button("🔄  New Participant"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step active"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Financial<br>Profile</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">All figures are monthly unless stated otherwise. Enter your best estimates — exact precision is not required.</div>', unsafe_allow_html=True)

    with st.form("input_form"):
        st.markdown('<div class="section-header">Location</div>', unsafe_allow_html=True)
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield",
                           "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
        addr       = st.selectbox("Suburb of Residence", suburbs)
        custom_sub = st.text_input("If 'Other', please specify:", placeholder="e.g. Chatswood")
        final_addr = custom_sub.strip() if addr == "Other" else addr

        st.markdown('<div class="section-header">Income</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            inc    = st.number_input("Monthly Income (AUD $)", min_value=0, max_value=15000, value=3200, step=50)
        with col2:
            p_supp = st.radio("Receiving Family Financial Support?", ["No", "Yes"], horizontal=True)
        p_amt = st.number_input("Family Support Amount ($/month) — enter 0 if none", min_value=0, max_value=5000, value=0, step=50)

        st.markdown('<div class="section-header">Core Weekly Expenses</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            rent  = st.number_input("Rent ($/week)",       min_value=0, max_value=2000, value=450, step=10)
        with col2:
            groc  = st.number_input("Groceries ($/week)",  min_value=0, max_value=500,  value=140, step=10)
        with col3:
            trans = st.number_input("Transport ($/week)",  min_value=0, max_value=300,  value=45,  step=5)

        st.markdown('<div class="section-header">Discretionary Spending</div>', unsafe_allow_html=True)
        uber = st.slider("Uber Eats / Eating Out / Lifestyle ($/week)", min_value=0, max_value=800, value=120, step=10)

        st.markdown('<div class="section-header">Financial Position</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            bills   = st.number_input("Fixed Bills ($/month)",    min_value=0, max_value=1000,   value=150,  step=10)
        with col2:
            remit   = st.number_input("Remittances ($/month)",    min_value=0, max_value=3000,   value=0,    step=50)
        with col3:
            savings = st.number_input("Emergency Savings ($)",    min_value=0, max_value=100000, value=2000, step=100)

        st.markdown('<div class="section-header">Background</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            lit    = st.select_slider("Financial Literacy Level", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        with col2:
            months = st.number_input("Months Living in Sydney", min_value=1, max_value=120, value=12)

        meals = st.radio("Have you skipped meals due to lack of money in the past month?", ["No", "Yes"], horizontal=True)

        st.markdown("---")
        submitted = st.form_submit_button("⚡  GENERATE AI RESILIENCE REPORT")

    if submitted:
        if addr == "Other" and not final_addr:
            st.warning("Please specify your suburb.")
        else:
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
                    if id_already_submitted(sheet, st.session_state.participant_id):
                        st.error("⚠️ This participant ID has already submitted.")
                        st.session_state.data_saved = True
                        st.stop()

                    sydney_time = datetime.utcnow() + timedelta(hours=11)
                    pre = st.session_state.get("pre", {"stress": "", "confidence": "", "ai_trust": ""})

                    row = [
                        st.session_state.participant_id,              # 1  Unique_ID
                        sydney_time.strftime("%d %b %Y  %I:%M %p"),  # 2  Timestamp
                        "Yes",                                        # 3  Consent
                        rent,                                         # 4  Weekly Rent
                        inc,                                          # 5  Monthly Income
                        final_addr,                                   # 6  Sydney Area
                        uber,                                         # 7  Weekly Discretionary
                        pre["stress"],                                # 8  PRE_FinancialStress
                        pre["confidence"],                            # 9  PRE_SpendingConfidence
                        pre["ai_trust"],                              # 10 PRE_AITrustBaseline
                        res["score"],                                 # 11 Resilience_Score
                        meals,                                        # 12 Skipped_Meals
                        p_supp,                                       # 13 Parental_Support_YN
                        remit,                                        # 14 Monthly_Remittance
                        p_amt,                                        # 15 Parental_Support_Amt
                        savings,                                      # 16 Emergency_Savings
                        trans,                                        # 17 Weekly_Transport
                        lit,                                          # 18 Financial_Literacy
                        months,                                       # 19 Months_in_Sydney
                        "", "", "", "",                               # 20–23 POST Trust (filled later)
                        "", "", "",                                   # 24–26 POST PU (filled later)
                        "",                                           # 27 POST_BehaviouralIntent
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
# STEP: RESULTS  (AI dashboard + post-survey)
# ══════════════════════════════════════════════
elif st.session_state.step == "results":
    ai   = st.session_state.res
    data = st.session_state.data

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step active"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br>Dashboard</div>', unsafe_allow_html=True)

    surplus_display = f"+${ai['surplus']:,.2f}" if ai['surplus'] >= 0 else f"-${abs(ai['surplus']):,.2f}"

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <span class="metric-value">{ai['score']}</span>
            <div class="metric-label">Resilience Score</div>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color:#a78bfa">{ai['runway']}</span>
            <div class="metric-label">Runway (months)</div>
        </div>
        <div class="metric-card">
            <span class="metric-value" style="color:#34d399">{ai['prob']}%</span>
            <div class="metric-label">Stability Prob.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    flags_html = "".join(f"<li style='margin:7px 0'>{f}</li>" for f in ai['flags']) \
                 if ai['flags'] else "<li>✅ No critical stress indicators detected.</li>"

    st.markdown(f"""
    <div class="analysis-box">
        <b>AI Analysis — {data['addr']}</b><br><br>
        Housing costs represent <span class="highlight">{ai['rent_pct']:.1f}%</span> of total income,
        and discretionary spending accounts for <span class="highlight-pink">{ai['uber_pct']:.1f}%</span>.
        Monthly surplus is <span class="highlight">{surplus_display}</span> with a financial runway of
        <span class="highlight-cyan">{ai['runway']} months</span>.<br><br>
        <b>Risk Indicators:</b>
        <ul style="margin:10px 0 0 0; padding-left:20px">{flags_html}</ul>
    </div>""", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊  Spending", "📈  Benchmarks", "🔬  Score Logic", "💡  Recommendations"
    ])

    with tab1:
        st.markdown('<div class="section-header">Monthly Expense Breakdown</div>', unsafe_allow_html=True)
        fig_pie = px.pie(
            values=list(ai['exp_breakdown'].values()),
            names=list(ai['exp_breakdown'].keys()),
            hole=0.58, color_discrete_sequence=COLORS,
        )
        fig_pie.update_layout(**CHART_LAYOUT, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)))
        fig_pie.update_traces(textfont_color="#e2e8f0", marker=dict(line=dict(color="#06091a", width=2)))
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown('<div class="section-header">Income vs Total Expenses</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Total Income", "Total Expenses", "Monthly Surplus"],
            y=[ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)],
            marker_color=["#4ade80", "#f87171", "#60a5fa"],
            marker_line=dict(color="#06091a", width=2),
            text=[f"${v:,.0f}" for v in [ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)]],
            textposition="outside", textfont=dict(color="#e2e8f0", size=13),
        ))
        fig_bar.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(showgrid=False, showticklabels=False),
            xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#64748b")),
            showlegend=False, height=320,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown('<div class="section-header">Spend Categories as % of Income</div>', unsafe_allow_html=True)
        categories = list(ai['exp_breakdown'].keys())
        pct_vals   = [round(v / ai['m_inc'] * 100, 1) for v in ai['exp_breakdown'].values()]
        fig_h = go.Figure(go.Bar(
            x=pct_vals, y=categories, orientation='h',
            marker=dict(color=COLORS[:len(categories)], line=dict(color="#06091a", width=2)),
            text=[f"{p}%" for p in pct_vals],
            textposition="outside", textfont=dict(color="#e2e8f0"),
        ))
        fig_h.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#64748b")),
            showlegend=False, height=300,
        )
        st.plotly_chart(fig_h, use_container_width=True)

    with tab2:
        st.markdown('<div class="section-header">Your Spending vs Evidence-Based Benchmarks</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="analysis-box" style="font-size:0.85rem">
        Benchmarks drawn from AHURI (2023) housing stress thresholds and adapted 50/30/20 budgeting
        guidelines for Sydney international students. The
        <span style="color:#60a5fa;font-weight:600">blue marker</span>
        shows your position against each recommended range.
        </div>""", unsafe_allow_html=True)

        benchmarks = [
            ("Housing % of Income",        ai['rent_pct'],  25, 30, "%"),
            ("Discretionary % of Income",  ai['uber_pct'],  10, 15, "%"),
            ("Groceries % of Income",      ai['groc_pct'],  10, 18, "%"),
            ("Transport % of Income",      ai['trans_pct'],  5, 12, "%"),
            ("Savings Rate",               ai['save_rate'],  20, 30, "%"),
        ]
        for label, val, rec_lo, rec_hi, unit in benchmarks:
            color = "#4ade80" if rec_lo <= val <= rec_hi else ("#a78bfa" if val < rec_lo else "#f87171")
            pct_w = min(val / 50 * 100, 100)
            st.markdown(f"""
            <div class="bench-row">
                <div class="bench-label">{label} &nbsp;
                    <span style="font-family:'DM Mono';color:{color};font-weight:600">{val}{unit}</span>
                    <span style="font-size:0.7rem;color:#334155"> · recommended {rec_lo}–{rec_hi}{unit}</span>
                </div>
                <div class="bench-track">
                    <div class="bench-fill" style="width:{pct_w:.0f}%;background:{color}55"></div>
                    <div class="bench-marker" style="left:{min(pct_w, 98):.0f}%"></div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Spending Radar</div>', unsafe_allow_html=True)
        radar_cats = ["Housing", "Groceries", "Lifestyle", "Transport", "Bills", "Remittance"]
        radar_vals = [
            ai['rent_pct'], ai['groc_pct'], ai['uber_pct'], ai['trans_pct'],
            round(float(data['bills']) / ai['m_inc'] * 100, 1),
            round(float(data['remit']) / ai['m_inc'] * 100, 1),
        ]
        bench_vals = [28, 14, 12, 8, 5, 5]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=bench_vals + [bench_vals[0]], theta=radar_cats + [radar_cats[0]],
            fill='toself', name='Benchmark',
            line=dict(color='#4ade80', dash='dash', width=1.5),
            fillcolor='rgba(74,222,128,0.05)',
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=radar_vals + [radar_vals[0]], theta=radar_cats + [radar_cats[0]],
            fill='toself', name='Your Profile',
            line=dict(color='#60a5fa', width=2),
            fillcolor='rgba(96,165,250,0.1)',
        ))
        fig_radar.update_layout(
            **CHART_LAYOUT,
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0, 50], color='#334155', gridcolor='#1a2a4a'),
                angularaxis=dict(color='#64748b', gridcolor='#1a2a4a'),
            ),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)), height=400,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with tab3:
        st.markdown('<div class="section-header">Score Methodology</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="formula-box">
            <span class="f1">C1 · Surplus Ratio         (max 35 pts)</span>
            <span class="cite">  — Carroll (1997) buffer stock theory</span><br>
            <span class="f2">C2 · Housing Stress         (max 25 pts)</span>
            <span class="cite">  — AHURI (2023) 30% income threshold</span><br>
            <span class="f3">C3 · Emergency Buffer       (max 20 pts)</span>
            <span class="cite">  — Deaton (1991) ≥3 months recommended</span><br>
            <span class="f1">C4 · Financial Literacy     (max 10 pts)</span>
            <span class="cite">  — Lusardi & Mitchell (2014)</span><br>
            <span class="f2">C5 · Food Security          (max 10 pts)</span>
            <span class="cite">  — Gundersen & Ziliak (2015)</span><br>
            <span class="f3">Total → clamped to [5, 100]</span>
        </div>""", unsafe_allow_html=True)

        components = ai['score_components']
        values     = list(components.values())
        running    = sum(values)
        measures   = ["relative"] * len(values) + ["total"]
        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=measures,
            x=list(components.keys()) + ["Final Score"],
            y=values + [running],
            connector=dict(line=dict(color="#1a2a4a", width=1)),
            increasing=dict(marker_color="#4ade80"),
            decreasing=dict(marker_color="#f87171"),
            totals=dict(marker_color="#60a5fa"),
            text=[f"{v:+.1f}" for v in values] + [f"{running:.0f}"],
            textposition="outside", textfont=dict(color="#e2e8f0", size=11),
        ))
        fig_wf.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(showgrid=False, range=[min(0, min(values)) - 8, max(running, 100) + 18]),
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#64748b")),
            showlegend=False, height=400,
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        score_color = "#4ade80" if ai['score'] >= 60 else ("#60a5fa" if ai['score'] >= 35 else "#f87171")
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
                <div class="i-value" style="color:#a78bfa">{ai['lit_score']}/90</div>
                <div class="i-sub">Level: {data['lit']} (Lusardi & Mitchell)</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Monthly Surplus</div>
                <div class="i-value" style="color:{'#4ade80' if ai['surplus']>=0 else '#f87171'}">{surplus_display}</div>
                <div class="i-sub">Income minus all expenses</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Stability Probability</div>
                <div class="i-value" style="color:#34d399">{ai['prob']}%</div>
                <div class="i-sub">Logistic model on surplus ratio</div>
            </div>
        </div>""", unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="section-header">AI-Generated Recommendations</div>', unsafe_allow_html=True)
        recs = []
        if ai['rent_pct'] > 30:
            recs.append(("🏠 Housing Stress", f"Rent is {ai['rent_pct']:.1f}% of income — above AHURI's 30% stress threshold. Shared accommodation in Auburn, Parramatta, or Hurstville typically reduces housing costs by 15–25%."))
        if ai['uber_pct'] > 15:
            saving = round(float(data['uber']) * 4.33 * 0.4)
            recs.append(("🍔 Discretionary Spending", f"Cutting lifestyle spend by 40% frees ~${saving}/month. Meal prepping and using an Opal card instead of rideshare are effective first steps."))
        if ai['runway'] < 3:
            recs.append(("💰 Emergency Buffer", f"At {ai['runway']} months, your buffer is below the 3-month minimum (Deaton 1991). Saving $50–100/week consistently would close this gap within a year."))
        if float(data['remit']) > ai['m_inc'] * 0.15:
            recs.append(("💸 Remittance Efficiency", "Remittances exceed 15% of income. Services such as Wise or Remitly typically offer lower transfer fees — batching monthly transfers also reduces fixed costs."))
        if data['lit'] == "Novice":
            recs.append(("📚 Financial Literacy", "Free resources: ASIC's MoneySmart platform, Student Edge, and your university's financial counselling service are strong starting points."))
        if data['meals'] == "Yes":
            recs.append(("🍱 Food Security", "Meal-skipping is a serious hardship indicator (Gundersen & Ziliak 2015). Free meals are available through most Sydney university student hubs; OzHarvest and Foodbank NSW offer emergency food support."))
        if ai['surplus'] < 0:
            recs.append(("⚡ Urgent: Monthly Deficit", f"Expenditure exceeds income by ${abs(ai['surplus']):,.0f}/month. Contact your university's financial hardship office — emergency grants and interest-free loans may be available."))
        if not recs:
            recs.append(("✅ On Track", "No critical stress indicators detected. Maintain your surplus and consider directing it toward your emergency buffer to reach the 3-month target."))

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
            line=dict(color="#60a5fa", width=2.5),
            fill='tozeroy', fillcolor='rgba(96,165,250,0.05)',
        ))
        fig_proj.add_trace(go.Scatter(
            x=months_proj, y=proj_opt, name="If 20% more saved",
            line=dict(color="#4ade80", width=2, dash='dash'),
        ))
        fig_proj.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(title="Month", showgrid=False, color="#475569"),
            yaxis=dict(title="Savings (AUD $)", showgrid=False, color="#475569"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)), height=320,
        )
        st.plotly_chart(fig_proj, use_container_width=True)

    # ── POST-SURVEY ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">Post-Exposure Evaluation</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="font-size:0.9rem">Now that you have seen the AI report, please answer the following questions honestly. All items use a 1–5 scale (1 = Strongly Disagree, 5 = Strongly Agree).</div>', unsafe_allow_html=True)

    with st.form("post_form"):

        # ── Section A: McKnight et al. (2011) Trust in AI — 4 items ──────────
        st.markdown('<div class="section-header">Section A · Trust in AI  <span style="color:#334155;font-size:0.58rem;font-family:DM Mono">McKnight et al. (2011)</span></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">A1. This AI system is competent and effective at analysing financial data.</div>
            <span class="scale-cite">Trusting Belief — Competence · McKnight et al. (2011)</span>
        </div>""", unsafe_allow_html=True)
        t_competence = st.radio("a1", LIKERT_5, horizontal=True, key="t_comp", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">A2. This AI system appears to act in my best interest.</div>
            <span class="scale-cite">Trusting Belief — Benevolence · McKnight et al. (2011)</span>
        </div>""", unsafe_allow_html=True)
        t_benevolence = st.radio("a2", LIKERT_5, horizontal=True, key="t_bene", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">A3. This AI system provides an honest assessment of my financial situation.</div>
            <span class="scale-cite">Trusting Belief — Integrity · McKnight et al. (2011)</span>
        </div>""", unsafe_allow_html=True)
        t_integrity = st.radio("a3", LIKERT_5, horizontal=True, key="t_integ", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">A4. I would rely on this AI system when making personal financial decisions.</div>
            <span class="scale-cite">Trust Intention · McKnight et al. (2011)</span>
        </div>""", unsafe_allow_html=True)
        t_intention = st.radio("a4", LIKERT_5, horizontal=True, key="t_intent", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)

        # ── Section B: Perceived Usefulness — PRIMARY DV ──────────────────────
        st.markdown('<div class="section-header">Section B · Perceived Usefulness  <span style="color:#334155;font-size:0.58rem;font-family:DM Mono">Davis (1989) — Primary Dependent Variable</span></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">B1. This AI report improved my understanding of my current financial situation.</div>
            <span class="scale-cite">PU — Enhanced Understanding · Davis (1989)</span>
        </div>""", unsafe_allow_html=True)
        pu_understanding = st.radio("b1", LIKERT_5, horizontal=True, key="pu_und", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">B2. This AI report is useful for managing my finances as a student in Sydney.</div>
            <span class="scale-cite">PU — Task Utility · Davis (1989)</span>
        </div>""", unsafe_allow_html=True)
        pu_useful = st.radio("b2", LIKERT_5, horizontal=True, key="pu_use", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">B3. Using this AI report would help me make better financial decisions.</div>
            <span class="scale-cite">PU — Decision Aid · Davis (1989)</span>
        </div>""", unsafe_allow_html=True)
        pu_decision = st.radio("b3", LIKERT_5, horizontal=True, key="pu_dec", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)

        # ── Section C: Behavioural Intent ─────────────────────────────────────
        st.markdown('<div class="section-header">Section C · Behavioural Intention</div>', unsafe_allow_html=True)
        intent = st.radio(
            "After seeing this AI report, what is your most likely next step?",
            [
                "Reduce discretionary spending (e.g. eating out, lifestyle)",
                "Seek cheaper housing or move to a different suburb",
                "Look for additional income sources",
                "No change planned",
            ],
        )

        st.markdown("---")
        lock = st.form_submit_button("🔒  SUBMIT & LOCK RESPONSE")

    if lock:
        with st.spinner("Locking your response..."):
            sheet = connect_to_sheet()
            if sheet and st.session_state.get("target_row"):
                try:
                    row_idx = st.session_state.target_row
                    # Write cols 20–27 (T through AA in spreadsheet)
                    post_vals = [[
                        likert_val(t_competence),      # 20 POST_Trust_Competence
                        likert_val(t_benevolence),     # 21 POST_Trust_Benevolence
                        likert_val(t_integrity),       # 22 POST_Trust_Integrity
                        likert_val(t_intention),       # 23 POST_Trust_Intention
                        likert_val(pu_understanding),  # 24 POST_PU_Understanding
                        likert_val(pu_useful),         # 25 POST_PU_Useful
                        likert_val(pu_decision),       # 26 POST_PU_DecisionAid
                        intent,                        # 27 POST_BehaviouralIntent
                    ]]
                    sheet.update(post_vals, f"T{row_idx}:AA{row_idx}")
                    st.session_state.last_id = st.session_state.participant_id
                    st.session_state.step    = "finished"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save post-survey: {e}")
            elif not st.session_state.get("target_row"):
                st.error("⚠️ Row reference lost — please restart the survey.")
            else:
                st.error("❌ Could not connect to sheet.")
