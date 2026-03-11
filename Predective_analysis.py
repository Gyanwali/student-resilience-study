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

# ── SHEET COLUMN MAP (1-indexed) ─────────────────────────────────────────
# Original 19 columns — unchanged, no need to touch your existing sheet:
#  1  Unique_ID
#  2  Timestamp
#  3  Consent
#  4  Weekly Rent (AUD)
#  5  Monthly Income (AUD)
#  6  Sydney Area
#  7  Weekly UberEats
#  8  Trust Level          ← repurposed: POST_AITrust (1–5)
#  9  AI Usefulness        ← repurposed: POST_PU_Composite (avg of B1–B3)
# 10  Resilience Score
# 11  Skipped Meals
# 12  Parental Support Y/N
# 13  Monthly Remittance
# 14  Parental Support Amt
# 15  Emergency Savings
# 16  Weekly Transport
# 17  Financial Literacy
# 18  Months in Sydney
# 19  Behavioural Intent
# ── 4 NEW columns added to the right ────────────────────────────────────
# 20  PRE_AITrust          ← single pre-exposure baseline (1–5)
# 21  POST_PU_Understanding
# 22  POST_PU_Useful
# 23  POST_PU_DecisionAid
# ─────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Resilience Lab AI", page_icon="🛡️", layout="centered")

COLORS = ["#F43F5E", "#F59E0B", "#10B981", "#6366F1", "#0EA5E9", "#EC4899"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Playfair+Display:wght@700;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* ═══════════════════════════════════════════
   CSS VARIABLES — Light mode (default)
═══════════════════════════════════════════ */
:root {
    --bg:          #FAFAF8;
    --bg-card:     #FFFFFF;
    --bg-input:    #F5F4F0;
    --bg-subtle:   #F0EEE8;
    --border:      #E2DDD6;
    --border-med:  #C9C2B8;
    --text-primary:#1C1917;
    --text-body:   #44403C;
    --text-muted:  #78716C;
    --text-faint:  #A8A29E;
    --coral:       #F43F5E;
    --teal:        #0D9488;
    --amber:       #D97706;
    --indigo:      #4F46E5;
    --green:       #059669;
    --red:         #DC2626;
    --coral-soft:  #FFF1F2;
    --teal-soft:   #F0FDFA;
    --amber-soft:  #FFFBEB;
    --indigo-soft: #EEF2FF;
}

/* ── Dark mode overrides ── */
@media (prefers-color-scheme: dark) {
    :root {
        --bg:          #111110;
        --bg-card:     #1C1B18;
        --bg-input:    #252420;
        --bg-subtle:   #2A2926;
        --border:      #333230;
        --border-med:  #4A4845;
        --text-primary:#F5F5F0;
        --text-body:   #D6D3CE;
        --text-muted:  #A8A29E;
        --text-faint:  #78716C;
        --coral-soft:  #3D1219;
        --teal-soft:   #0D2B28;
        --amber-soft:  #2D1F08;
        --indigo-soft: #1A1840;
    }
}

/* ═══════════════════════════════════════════
   BASE
═══════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: var(--text-body);
}
.stApp {
    background: var(--bg) !important;
    color: var(--text-body) !important;
}
#MainMenu, footer, header { visibility: hidden; }

/* Animated top stripe */
@keyframes stripe-slide {
    0%   { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}
.stApp::before {
    content: ''; display: block; height: 4px;
    background: linear-gradient(90deg, #F43F5E, #F59E0B, #10B981, #6366F1, #F43F5E);
    background-size: 200% auto;
    animation: stripe-slide 4s linear infinite;
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
}

/* ═══════════════════════════════════════════
   WIDGET OVERRIDES
═══════════════════════════════════════════ */
label,
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] {
    color: var(--text-body) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Inputs */
input[type="number"], input[type="text"],
.stTextInput input, .stNumberInput input {
    background: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: border-color .2s, box-shadow .2s;
}
input:focus {
    border-color: var(--coral) !important;
    box-shadow: 0 0 0 3px rgba(244,63,94,0.12) !important;
    outline: none !important;
}

/* Selectbox */
.stSelectbox > div > div,
div[data-baseweb="select"] > div {
    background: var(--bg-input) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div { color: var(--text-primary) !important; }
ul[data-baseweb="menu"],
div[data-baseweb="popover"] ul {
    background: var(--bg-card) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
}
ul[data-baseweb="menu"] li {
    color: var(--text-body) !important;
    background: transparent !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
ul[data-baseweb="menu"] li:hover {
    background: var(--coral-soft) !important;
    color: var(--coral) !important;
}

/* Radio buttons */
.stRadio > div { gap: 8px !important; flex-wrap: wrap !important; }
.stRadio label {
    color: var(--text-body) !important;
    background: var(--bg-input) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    cursor: pointer;
    transition: all .18s ease;
}
.stRadio label:hover {
    border-color: var(--coral) !important;
    color: var(--coral) !important;
    background: var(--coral-soft) !important;
}
.stRadio [aria-checked="true"] + label,
.stRadio input:checked + div {
    border-color: var(--coral) !important;
    background: var(--coral-soft) !important;
    color: var(--coral) !important;
    font-weight: 700 !important;
}

/* Slider */
.stSlider > div > div > div > div { background: var(--coral) !important; }
.stSlider [data-baseweb="slider"] > div:first-child { background: var(--border) !important; }
.stSlider p, .stSlider span { color: var(--text-muted) !important; }

/* Number input spinners */
.stNumberInput button {
    background: var(--bg-input) !important;
    border-color: var(--border) !important;
    color: var(--text-body) !important;
}
.stNumberInput button:hover {
    background: var(--coral-soft) !important;
    color: var(--coral) !important;
}

/* Checkbox */
.stCheckbox label {
    color: var(--text-body) !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
}
.stCheckbox span { border-color: var(--border-med) !important; background: var(--bg-input) !important; }

/* Text */
.stApp p, .stMarkdown p {
    color: var(--text-body);
    line-height: 1.8;
}
.stForm { background: transparent !important; border: none !important; }

/* Submit / action buttons */
.stButton > button,
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #F43F5E 0%, #F97316 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    height: 3.2rem !important;
    width: 100% !important;
    box-shadow: 0 4px 14px rgba(244,63,94,0.3) !important;
    transition: transform .15s, box-shadow .15s !important;
}
.stButton > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(244,63,94,0.4) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-subtle) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1.5px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    border-radius: 7px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}
.stTabs [aria-selected="true"] {
    background: var(--coral) !important;
    color: #fff !important;
}

hr {
    border-color: var(--border) !important;
    margin: 2rem 0 !important;
}

/* ═══════════════════════════════════════════
   CUSTOM COMPONENTS
═══════════════════════════════════════════ */

/* Animated top badge */
.top-badge {
    font-family: 'Courier Prime', monospace;
    font-size: 0.68rem;
    color: var(--teal);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    border: 1.5px solid var(--teal);
    background: var(--teal-soft);
    display: inline-block;
    padding: 5px 16px;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-weight: 700;
}

/* Hero headings — Playfair Display for editorial impact */
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 3.4rem;
    font-weight: 900;
    color: var(--text-primary);
    line-height: 1.1;
    margin-bottom: 0.6rem;
}
.hero-title .accent { color: var(--coral); }

.hero-sub {
    font-size: 1rem;
    color: var(--text-muted);
    margin-bottom: 2rem;
    font-weight: 400;
    line-height: 1.75;
    max-width: 520px;
}

/* Section headings — clear, visible */
.section-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 2rem 0 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, var(--border), transparent);
    border-radius: 2px;
}

/* Subtle section labels (inside forms) */
.section-header {
    font-family: 'Courier Prime', monospace;
    font-size: 0.68rem;
    color: var(--coral);
    text-transform: uppercase;
    letter-spacing: 0.2em;
    margin: 1.8rem 0 0.7rem 0;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-header::before {
    content: '';
    width: 18px;
    height: 2px;
    background: var(--coral);
    border-radius: 2px;
    display: inline-block;
}

/* PID chip */
.pid-chip {
    font-family: 'Courier Prime', monospace;
    background: var(--amber-soft);
    border: 1.5px solid var(--amber);
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 0.72rem;
    color: var(--amber);
    display: inline-block;
    margin-bottom: 1.2rem;
    letter-spacing: 0.1em;
    font-weight: 700;
}

/* Progress bar */
.step-bar { display: flex; gap: 6px; margin-bottom: 2rem; }
.step        { flex: 1; height: 5px; border-radius: 3px; background: var(--border); }
.step.done   { background: var(--teal); }
.step.active { background: linear-gradient(90deg, var(--coral), var(--amber)); }

/* Info / intro card */
.card {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 1.2rem;
    color: var(--text-body);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* Metric grid — each card gets its own vivid accent */
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 1.6rem 0; }
.metric-card {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-radius: 14px;
    padding: 22px 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transition: transform .2s;
}
.metric-card:hover { transform: translateY(-2px); }
.metric-card-1 { border-top: 4px solid var(--coral); }
.metric-card-2 { border-top: 4px solid var(--teal); }
.metric-card-3 { border-top: 4px solid var(--amber); }
.metric-value {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    font-weight: 900;
    display: block;
    line-height: 1;
}
.metric-label {
    font-size: 0.65rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-top: 8px;
    font-weight: 600;
}

/* Analysis / AI output box */
.analysis-box {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-left: 5px solid var(--coral);
    border-radius: 12px;
    padding: 22px 26px;
    margin: 1.6rem 0;
    line-height: 1.9;
    color: var(--text-body);
    font-size: 0.93rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.analysis-box b { color: var(--text-primary); }
.highlight      { color: var(--coral);  font-family: 'Courier Prime', monospace; font-weight: 700; }
.highlight-teal { color: var(--teal);   font-family: 'Courier Prime', monospace; font-weight: 700; }
.highlight-amber{ color: var(--amber);  font-family: 'Courier Prime', monospace; font-weight: 700; }

/* Insight grid */
.insight-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; margin: 1.2rem 0; }
.insight-card {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.insight-card .i-label {
    font-family: 'Courier Prime', monospace;
    font-size: 0.63rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 6px;
    font-weight: 700;
}
.insight-card .i-value {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text-primary);
}
.insight-card .i-sub { font-size: 0.76rem; color: var(--text-muted); margin-top: 4px; }

/* Formula box */
.formula-box {
    background: var(--bg-subtle);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 18px 20px;
    font-family: 'Courier Prime', monospace;
    font-size: 0.82rem;
    color: var(--text-body);
    margin: 1rem 0;
    line-height: 2.2;
}
.formula-box .f1 { color: var(--coral); font-weight: 700; }
.formula-box .f2 { color: var(--teal);  font-weight: 700; }
.formula-box .f3 { color: var(--amber); font-weight: 700; }
.formula-box .cite { color: var(--text-faint); font-size: 0.71rem; }

/* Benchmark bars */
.bench-row   { margin: 14px 0; }
.bench-label { font-size: 0.84rem; color: var(--text-body); margin-bottom: 7px; font-weight: 500; }
.bench-track {
    background: var(--bg-subtle);
    border: 1px solid var(--border);
    border-radius: 4px;
    height: 10px;
    width: 100%;
    position: relative;
}
.bench-fill  { height: 10px; border-radius: 4px; }
.bench-marker {
    position: absolute;
    top: -5px;
    width: 3px;
    height: 20px;
    background: var(--text-primary);
    border-radius: 2px;
    opacity: 0.7;
}

/* Recommendation cards */
.rec-card {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-left: 5px solid var(--teal);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: transform .2s;
}
.rec-card:hover { transform: translateX(3px); }
.rec-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.85rem;
    color: var(--teal);
    font-weight: 700;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.rec-body { font-size: 0.9rem; color: var(--text-body); line-height: 1.75; }

/* Scale question blocks */
.scale-block {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.scale-q {
    font-size: 1rem;
    color: var(--text-primary);
    font-weight: 600;
    margin-bottom: 4px;
    line-height: 1.5;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.scale-cite {
    font-family: 'Courier Prime', monospace;
    font-size: 0.66rem;
    color: var(--text-faint);
    margin-bottom: 12px;
    display: block;
}
.scale-anchors {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    color: var(--text-faint);
    margin-top: 4px;
    font-family: 'Courier Prime', monospace;
    font-weight: 700;
}

/* Locked box */
.locked-box {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-left: 5px solid var(--coral);
    border-radius: 12px;
    padding: 24px 28px;
    margin: 1.6rem 0;
    line-height: 1.8;
    color: var(--text-body);
    font-size: 0.93rem;
    text-align: center;
}
.locked-box .lock-icon { font-size: 2.4rem; display: block; margin-bottom: 10px; }
.locked-box .lock-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem;
    color: var(--coral);
    font-weight: 700;
    margin-bottom: 8px;
}

/* Pre-notice banner */
.pre-notice {
    background: var(--amber-soft);
    border: 1.5px solid var(--amber);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 1.4rem;
    font-size: 0.88rem;
    color: var(--text-body);
    line-height: 1.7;
}
.pre-notice b { color: var(--amber); }

/* ── Finish screen ── */
.finish-score-ring {
    width: 160px; height: 160px;
    border-radius: 50%;
    border: 5px solid var(--border);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1.6rem auto;
}
.finish-score-num {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 900;
    line-height: 1;
}
.finish-score-lbl {
    font-size: 0.65rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 5px;
    font-weight: 700;
}
.finish-band {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 0.5rem;
}
.finish-insight {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-left: 5px solid var(--teal);
    border-radius: 12px;
    padding: 20px 24px;
    margin: 1.4rem 0;
    font-size: 0.95rem;
    color: var(--text-body);
    line-height: 1.85;
}
.finish-insight b { color: var(--text-primary); }
.finish-id {
    font-family: 'Courier Prime', monospace;
    font-size: 0.82rem;
    color: var(--text-faint);
    text-align: center;
    margin-top: 1.4rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#78716C", family="Plus Jakarta Sans"),
    margin=dict(t=30, b=30, l=10, r=10),
)

LIKERT_5 = ["1", "2", "3", "4", "5"]


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
    response = sheet.append_row(row_data, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")
    match = re.search(r':.*?(\d+)$', response["updates"]["updatedRange"])
    return int(match.group(1)) if match else None

def id_already_submitted(sheet, pid):
    try:
        return pid in sheet.col_values(1)
    except Exception:
        return False


# ──────────────────────────────────────────────
# SCORING MODEL
# ──────────────────────────────────────────────
# C1 Surplus Ratio   (35 pts) — Carroll (1997)
# C2 Housing Stress  (25 pts) — AHURI (2023)  threshold: 30% of income
# C3 Emergency Buffer(20 pts) — Deaton (1991) target: ≥3 months expenses
# C4 Fin. Literacy   (10 pts) — Lusardi & Mitchell (2014)
# C5 Food Security   (10 pts) — Gundersen & Ziliak (2015)
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

    z    = (surplus / (m_exp if m_exp > 0 else 1)) * 5
    prob = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 \
           else round(max(5.0, 25.0 + (surplus / 500)), 1)

    lit_map   = {"Novice": 25, "Intermediate": 60, "Advanced": 90}
    lit_score = lit_map[data['lit']]

    sir       = surplus / m_inc if m_inc > 0 else -1.0
    c_surplus = max(0.0, min(35.0, (sir + 0.5) * 35))

    rent_pct = (exp_vals["Housing"] / m_inc) * 100 if m_inc > 0 else 100
    if   rent_pct <= 25: c_housing = 25
    elif rent_pct <= 30: c_housing = 18
    elif rent_pct <= 40: c_housing = 8
    else:                c_housing = 0

    if   runway >= 6: c_buffer = 20
    elif runway >= 3: c_buffer = 14
    elif runway >= 1: c_buffer = 6
    else:             c_buffer = 0

    c_literacy = round(lit_score * 0.111, 1)
    c_food     = 0 if data['meals'] == "Yes" else 10
    score      = int(min(max(round(c_surplus + c_housing + c_buffer + c_literacy + c_food), 5), 100))

    uber_pct  = round((exp_vals["Lifestyle"]  / m_inc) * 100, 1)
    groc_pct  = round((exp_vals["Groceries"]  / m_inc) * 100, 1)
    trans_pct = round((exp_vals["Transport"]  / m_inc) * 100, 1)
    remit_pct = round((exp_vals["Remittance"] / m_inc) * 100, 1)
    save_rate = round((max(surplus, 0) / m_inc) * 100, 1)

    flags = []
    if rent_pct > 30:
        flags.append(f"⚠️ Housing stress: <b>{rent_pct:.1f}%</b> of income — exceeds AHURI's 30% threshold.")
    if uber_pct > 15:
        flags.append(f"⚠️ Discretionary spend at <b>{uber_pct:.1f}%</b> — above the recommended 15%.")
    if runway < 3:
        flags.append(f"🔴 Emergency buffer: <b>{runway} months</b> — below the 3-month minimum (Deaton 1991).")
    if data['meals'] == "Yes":
        flags.append("🔴 Meal-skipping detected — indicator of acute financial hardship.")
    if surplus < 0:
        flags.append(f"🔴 Monthly deficit: <b>${abs(round(surplus)):,}</b> — spending exceeds income.")
    if remit_pct > 15:
        flags.append(f"⚠️ Remittance burden at <b>{remit_pct:.1f}%</b> — World Bank recommends below 15%.")

    return {
        "surplus": round(surplus, 2), "m_inc": round(m_inc, 2), "m_exp": round(m_exp, 2),
        "score": score, "prob": min(prob, 100.0), "runway": runway,
        "rent_pct": rent_pct, "uber_pct": uber_pct, "groc_pct": groc_pct,
        "trans_pct": trans_pct, "remit_pct": remit_pct, "save_rate": save_rate,
        "exp_breakdown": exp_vals, "flags": flags, "lit_score": lit_score,
        "score_components": {
            "Surplus Ratio": round(c_surplus, 1),
            "Housing Stress": round(c_housing, 1),
            "Emerg. Buffer": round(c_buffer, 1),
            "Fin. Literacy": round(c_literacy, 1),
            "Food Security": c_food,
        },
    }


def score_band(score):
    if score >= 65:
        return (
            "Financially Resilient", "#059669",
            "Your income comfortably covers expenses and you maintain a healthy buffer. "
            "Your <b>priority action</b> is to grow your emergency savings toward a 6-month runway."
        )
    elif score >= 40:
        return (
            "Moderately Resilient", "#0D9488",
            "Your finances are manageable but leave limited room for unexpected costs. "
            "Your <b>priority action</b> is to cut one discretionary category and redirect it to savings."
        )
    else:
        return (
            "Financially Vulnerable", "#F43F5E",
            "Your current spending pattern puts you at risk of financial hardship. "
            "Your <b>priority action</b> is to contact your university's financial counselling service this week."
        )


# ──────────────────────────────────────────────
# SESSION STATE INIT
# ──────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step           = "home"
    st.session_state.data_saved     = False
    st.session_state.participant_id = f"RES-{random.randint(100000, 999999)}"


# ══════════════════════════════════════════════
# STEP: FINISHED  — personalised thank-you
# ══════════════════════════════════════════════
if st.session_state.step == "finished":
    score = st.session_state.get("final_score", 0)
    label, colour, insight = score_band(score)
    colour_map = {"Financially Resilient": "var(--green)", "Moderately Resilient": "var(--teal)", "Financially Vulnerable": "var(--coral)"}
    colour = colour_map.get(label, "var(--coral)")

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step done"></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="top-badge">✓ Research Complete</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Thank <span class="accent">You</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Your response has been recorded and your data is securely stored.</div>', unsafe_allow_html=True)

    # Score ring
    st.markdown(f"""
    <div class="finish-score-ring" style="border-color:{colour}33">
        <span class="finish-score-num" style="color:{colour}">{score}</span>
        <span class="finish-score-lbl">out of 100</span>
    </div>
    <div class="finish-band" style="color:{colour}">{label}</div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="finish-insight">{insight}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="finish-id">Participant ID: {st.session_state.get("last_id","—")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="analysis-box" style="margin-top:1.2rem;font-size:0.85rem">You may now safely close this window. Your data will be used solely for academic research on financial resilience among international students in Sydney.</div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════
# STEP: HOME
# ══════════════════════════════════════════════
if st.session_state.step == "home":
    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="top-badge">🎓 Sydney · Academic Research · 2025</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br><span class="accent">Lab AI</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Examining how AI-generated financial analytics influence perceived usefulness and resilience among international students in Sydney.</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <div class="section-header">What to expect</div>
        Takes approximately <b>3–4 minutes</b> across four short stages:<br><br>
        <b>1.</b> One quick baseline question &nbsp;·&nbsp;
        <b>2.</b> Your anonymised financial profile &nbsp;·&nbsp;
        <b>3.</b> Your personalised AI resilience report &nbsp;·&nbsp;
        <b>4.</b> Three short evaluation questions<br><br>
        All responses are anonymised and used for academic purposes only.
    </div>""", unsafe_allow_html=True)

    consent = st.checkbox("I voluntarily consent to participate in this research study and understand my data will be anonymised.")
    if consent:
        if st.button("▶  BEGIN SURVEY"):
            st.session_state.step = "pre_survey"
            st.rerun()


# ══════════════════════════════════════════════
# STEP: PRE-SURVEY  (1 question, before AI exposure)
# ══════════════════════════════════════════════
elif st.session_state.step == "pre_survey":
    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step active"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Before We<br><span class="accent">Begin</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">One quick question before you see any AI analysis — your honest baseline view matters for this research.</div>', unsafe_allow_html=True)

    with st.form("pre_form"):
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">I trust AI-generated tools to provide useful guidance on personal financial matters.</div>
            <span class="scale-cite">Pre-exposure AI trust baseline — McKnight et al. (2011) &nbsp;|&nbsp; 1 = Strongly Disagree · 5 = Strongly Agree</span>
        </div>""", unsafe_allow_html=True)
        pre_trust = st.radio("pre_trust", LIKERT_5, horizontal=True, key="pre_trust_val", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("---")
        go = st.form_submit_button("NEXT  →  Financial Profile")

    if go:
        st.session_state.pre_ai_trust = int(pre_trust)
        st.session_state.step = "inputs"
        st.rerun()


# ══════════════════════════════════════════════
# STEP: INPUTS
# ══════════════════════════════════════════════
elif st.session_state.step == "inputs":

    if st.session_state.data_saved:
        st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step done"></div></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="locked-box">
            <span class="lock-icon">🔒</span>
            <div class="lock-title">Response Already Recorded</div>
            Participant <b style="color:#60a5fa">{st.session_state.participant_id}</b>
            has already submitted.<br><br>
            Please pass the device to the next participant.
        </div>""", unsafe_allow_html=True)
        if st.button("🔄  New Participant"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step active"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Your Financial<br><span class="accent">Profile</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">All figures are monthly unless stated. Best estimates are fine.</div>', unsafe_allow_html=True)

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
            p_supp = st.radio("Receiving Family Support?", ["No", "Yes"], horizontal=True)
        p_amt = st.number_input("Family Support Amount ($/month) — enter 0 if none", min_value=0, max_value=5000, value=0, step=50)

        st.markdown('<div class="section-header">Weekly Expenses</div>', unsafe_allow_html=True)
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
            bills   = st.number_input("Fixed Bills ($/month)",  min_value=0, max_value=1000,   value=150,  step=10)
        with col2:
            remit   = st.number_input("Remittances ($/month)",  min_value=0, max_value=3000,   value=0,    step=50)
        with col3:
            savings = st.number_input("Emergency Savings ($)",  min_value=0, max_value=100000, value=2000, step=100)

        st.markdown('<div class="section-header">Background</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            lit    = st.select_slider("Financial Literacy Level", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        with col2:
            months = st.number_input("Months Living in Sydney", min_value=1, max_value=120, value=12)

        meals = st.radio("Have you skipped meals due to lack of money in the past month?", ["No", "Yes"], horizontal=True)

        st.markdown("---")
        submitted = st.form_submit_button("⚡  GENERATE MY RESILIENCE REPORT")

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
                    row = [
                        st.session_state.participant_id,              # 1  Unique_ID
                        sydney_time.strftime("%d %b %Y  %I:%M %p"),  # 2  Timestamp
                        "Yes",                                        # 3  Consent
                        rent,                                         # 4  Weekly Rent
                        inc,                                          # 5  Monthly Income
                        final_addr,                                   # 6  Sydney Area
                        uber,                                         # 7  Weekly UberEats
                        "",                                           # 8  POST_AITrust     (filled after)
                        "",                                           # 9  POST_PU_Composite(filled after)
                        res["score"],                                 # 10 Resilience Score
                        meals,                                        # 11 Skipped Meals
                        p_supp,                                       # 12 Parental Support Y/N
                        remit,                                        # 13 Monthly Remittance
                        p_amt,                                        # 14 Parental Support Amt
                        savings,                                      # 15 Emergency Savings
                        trans,                                        # 16 Weekly Transport
                        lit,                                          # 17 Financial Literacy
                        months,                                       # 18 Months in Sydney
                        "",                                           # 19 Behavioural Intent (filled after)
                        st.session_state.get("pre_ai_trust", ""),    # 20 PRE_AITrust
                        "", "", "",                                   # 21–23 POST PU items  (filled after)
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
# STEP: RESULTS
# ══════════════════════════════════════════════
elif st.session_state.step == "results":
    ai   = st.session_state.res
    data = st.session_state.data

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step active"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br><span class="accent">Dashboard</span></div>', unsafe_allow_html=True)

    surplus_display = f"+${ai['surplus']:,.0f}" if ai['surplus'] >= 0 else f"-${abs(ai['surplus']):,.0f}"

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card metric-card-1">
            <span class="metric-value" style="color:var(--coral)">{ai['score']}</span>
            <div class="metric-label">Resilience Score</div>
        </div>
        <div class="metric-card metric-card-2">
            <span class="metric-value" style="color:var(--teal)">{ai['runway']}</span>
            <div class="metric-label">Runway (months)</div>
        </div>
        <div class="metric-card metric-card-3">
            <span class="metric-value" style="color:var(--amber)">{ai['prob']}%</span>
            <div class="metric-label">Stability Prob.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    flags_html = "".join(f"<li style='margin:7px 0'>{f}</li>" for f in ai['flags']) \
                 if ai['flags'] else "<li>✅ No critical stress indicators detected.</li>"

    st.markdown(f"""
    <div class="analysis-box">
        <b>AI Analysis — {data['addr']}</b><br><br>
        Housing costs represent <span class="highlight">{ai['rent_pct']:.1f}%</span> of total income
        and discretionary spending accounts for <span class="highlight-teal">{ai['uber_pct']:.1f}%</span>.
        Monthly surplus is <span class="highlight">{surplus_display}</span> with a financial runway of
        <span class="highlight-amber">{ai['runway']} months</span>.<br><br>
        <b>Risk Indicators:</b>
        <ul style="margin:10px 0 0 0;padding-left:20px">{flags_html}</ul>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊  Spending", "📈  Benchmarks", "🔬  Score Logic", "💡  Recommendations"])

    with tab1:
        st.markdown('<div class="section-header">Monthly Expense Breakdown</div>', unsafe_allow_html=True)
        fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()),
                         hole=0.58, color_discrete_sequence=COLORS)
        fig_pie.update_layout(**CHART_LAYOUT, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)))
        fig_pie.update_traces(textfont_color="#e2e8f0", marker=dict(line=dict(color="#06091a", width=2)))
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown('<div class="section-header">Income vs Expenses</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Total Income", "Total Expenses", "Monthly Surplus"],
            y=[ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)],
            marker_color=["#10B981", "#F43F5E", "#F59E0B"],
            marker_line=dict(color="rgba(0,0,0,0)", width=0),
            text=[f"${v:,.0f}" for v in [ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)]],
            textposition="outside", textfont=dict(color="#44403C", size=13),
        ))
        fig_bar.update_layout(**CHART_LAYOUT,
            yaxis=dict(showgrid=False, showticklabels=False),
            xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#64748b")),
            showlegend=False, height=300)
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.markdown('<div class="section-header">Your Spending vs Benchmarks</div>', unsafe_allow_html=True)
        benchmarks = [
            ("Housing % of Income",       ai['rent_pct'],  25, 30, "%"),
            ("Discretionary % of Income", ai['uber_pct'],  10, 15, "%"),
            ("Groceries % of Income",     ai['groc_pct'],  10, 18, "%"),
            ("Transport % of Income",     ai['trans_pct'],  5, 12, "%"),
            ("Savings Rate",              ai['save_rate'],  20, 30, "%"),
        ]
        for label, val, lo, hi, unit in benchmarks:
            color = "#4ade80" if lo <= val <= hi else ("#a78bfa" if val < lo else "#f87171")
            pct_w = min(val / 50 * 100, 100)
            st.markdown(f"""
            <div class="bench-row">
                <div class="bench-label">{label} &nbsp;
                    <span style="font-family:'DM Mono';color:{color};font-weight:600">{val}{unit}</span>
                    <span style="font-size:0.7rem;color:#334155"> · recommended {lo}–{hi}{unit}</span>
                </div>
                <div class="bench-track">
                    <div class="bench-fill" style="width:{pct_w:.0f}%;background:{color}55"></div>
                    <div class="bench-marker" style="left:{min(pct_w,98):.0f}%"></div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Spending Radar</div>', unsafe_allow_html=True)
        rcats = ["Housing", "Groceries", "Lifestyle", "Transport", "Bills", "Remittance"]
        rvals = [ai['rent_pct'], ai['groc_pct'], ai['uber_pct'], ai['trans_pct'],
                 round(float(data['bills']) / ai['m_inc'] * 100, 1),
                 round(float(data['remit']) / ai['m_inc'] * 100, 1)]
        bvals = [28, 14, 12, 8, 5, 5]
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(r=bvals+[bvals[0]], theta=rcats+[rcats[0]], fill='toself',
            name='Benchmark', line=dict(color='#10B981', dash='dash', width=2), fillcolor='rgba(16,185,129,0.07)'))
        fig_r.add_trace(go.Scatterpolar(r=rvals+[rvals[0]], theta=rcats+[rcats[0]], fill='toself',
            name='Your Profile', line=dict(color='#F43F5E', width=2.5), fillcolor='rgba(244,63,94,0.1)'))
        fig_r.update_layout(**CHART_LAYOUT,
            polar=dict(bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0,50], color='#334155', gridcolor='#1a2a4a'),
                angularaxis=dict(color='#64748b', gridcolor='#1a2a4a')),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)), height=380)
        st.plotly_chart(fig_r, use_container_width=True)

    with tab3:
        st.markdown('<div class="section-header">Score Methodology</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="formula-box">
            <span class="f1">C1 · Surplus Ratio    (max 35 pts)</span><span class="cite">  — Carroll (1997)</span><br>
            <span class="f2">C2 · Housing Stress   (max 25 pts)</span><span class="cite">  — AHURI (2023) 30% threshold</span><br>
            <span class="f3">C3 · Emerg. Buffer    (max 20 pts)</span><span class="cite">  — Deaton (1991) ≥3 months</span><br>
            <span class="f1">C4 · Fin. Literacy    (max 10 pts)</span><span class="cite">  — Lusardi & Mitchell (2014)</span><br>
            <span class="f2">C5 · Food Security    (max 10 pts)</span><span class="cite">  — Gundersen & Ziliak (2015)</span>
        </div>""", unsafe_allow_html=True)

        comps  = ai['score_components']
        vals   = list(comps.values())
        total  = sum(vals)
        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"]*len(vals)+["total"],
            x=list(comps.keys())+["Final Score"], y=vals+[total],
            connector=dict(line=dict(color="#E2DDD6", width=1)),
            increasing=dict(marker_color="#10B981"), decreasing=dict(marker_color="#F43F5E"),
            totals=dict(marker_color="#6366F1"),
            text=[f"{v:+.1f}" for v in vals]+[f"{total:.0f}"],
            textposition="outside", textfont=dict(color="#44403C", size=11),
        ))
        fig_wf.update_layout(**CHART_LAYOUT,
            yaxis=dict(showgrid=False, range=[0, max(total, 100)+18]),
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#64748b")),
            showlegend=False, height=380)
        st.plotly_chart(fig_wf, use_container_width=True)

        sc, lc = ("var(--green)" if ai['score']>=65 else "var(--teal)" if ai['score']>=40 else "var(--red)"), \
                 ("Strong" if ai['score']>=65 else "Moderate" if ai['score']>=40 else "Vulnerable")
        st.markdown(f"""
        <div class="insight-grid">
            <div class="insight-card">
                <div class="i-label">Final Score</div>
                <div class="i-value" style="color:{sc}">{ai['score']}/100</div>
                <div class="i-sub">Resilience: {lc}</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Monthly Surplus</div>
                <div class="i-value" style="color:{'var(--green)' if ai['surplus']>=0 else 'var(--red)'}">{surplus_display}</div>
                <div class="i-sub">Income minus all expenses</div>
            </div>
        </div>""", unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="section-header">Recommendations</div>', unsafe_allow_html=True)
        recs = []
        if ai['rent_pct'] > 30:
            recs.append(("🏠 Housing", f"Rent is {ai['rent_pct']:.1f}% of income — above AHURI's 30% stress threshold. Shared accommodation in Auburn or Parramatta can reduce costs by 15–25%."))
        if ai['uber_pct'] > 15:
            saving = round(float(data['uber']) * 4.33 * 0.4)
            recs.append(("🍔 Discretionary", f"Cutting lifestyle spend by 40% frees ~${saving}/month. Meal prepping 4 days a week is the single highest-impact change."))
        if ai['runway'] < 3:
            recs.append(("💰 Emergency Buffer", f"Only {ai['runway']} months of runway — target 3 months minimum (Deaton 1991). Even $50/week consistently will get you there."))
        if float(data['remit']) > ai['m_inc'] * 0.15:
            recs.append(("💸 Remittances", "Remittances exceed 15% of income. Wise or Remitly offer lower fees than banks — batch transfers monthly to cut fixed costs."))
        if data['meals'] == "Yes":
            recs.append(("🍱 Food Security", "Free meals are available through most Sydney university student hubs. OzHarvest and Foodbank NSW also provide emergency food support."))
        if ai['surplus'] < 0:
            recs.append(("⚡ Deficit", f"Spending ${abs(ai['surplus']):,.0f}/month more than you earn. Contact your university's financial hardship office — emergency grants may be available."))
        if not recs:
            recs.append(("✅ On Track", "No critical stress points. Keep your surplus steady and push your emergency buffer toward the 6-month mark."))

        for title, body in recs:
            st.markdown(f'<div class="rec-card"><div class="rec-title">{title}</div><div class="rec-body">{body}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">12-Month Savings Projection</div>', unsafe_allow_html=True)
        mths       = list(range(0, 13))
        cur_sav    = float(data['savings'])
        m_add      = max(ai['surplus'], 0)
        fig_proj   = go.Figure()
        fig_proj.add_trace(go.Scatter(x=mths, y=[cur_sav + m_add*m for m in mths],
            name="Current", line=dict(color="#6366F1", width=2.5),
            fill='tozeroy', fillcolor='rgba(99,102,241,0.07)'))
        fig_proj.add_trace(go.Scatter(x=mths, y=[cur_sav + m_add*1.2*m for m in mths],
            name="If 20% more saved", line=dict(color="#10B981", width=2, dash='dash')))
        fig_proj.update_layout(**CHART_LAYOUT,
            xaxis=dict(title="Month", showgrid=False, color="#475569"),
            yaxis=dict(title="Savings ($)", showgrid=False, color="#475569"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)), height=300)
        st.plotly_chart(fig_proj, use_container_width=True)

    # ── POST-SURVEY  (3 questions + 1 intent) ─────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">Evaluation  <span style="color:#334155;font-size:0.58rem;font-family:DM Mono">4 questions · takes 30 seconds</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="font-size:0.88rem;margin-bottom:1rem">Now that you have seen the AI report, please rate the following. Use 1–5 (1 = Strongly Disagree, 5 = Strongly Agree).</div>', unsafe_allow_html=True)

    with st.form("post_form"):

        # B1 — PU Understanding
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">B1. This AI report improved my understanding of my financial situation.</div>
            <span class="scale-cite">Perceived Usefulness — Davis (1989) · Primary DV</span>
        </div>""", unsafe_allow_html=True)
        pu1 = st.radio("b1", LIKERT_5, horizontal=True, key="pu1", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # B2 — PU Useful
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">B2. This AI report is useful for managing my finances as a student in Sydney.</div>
            <span class="scale-cite">Perceived Usefulness — Davis (1989) · Primary DV</span>
        </div>""", unsafe_allow_html=True)
        pu2 = st.radio("b2", LIKERT_5, horizontal=True, key="pu2", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # B3 — PU Decision Aid
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">B3. Using this AI report would help me make better financial decisions.</div>
            <span class="scale-cite">Perceived Usefulness — Davis (1989) · Primary DV</span>
        </div>""", unsafe_allow_html=True)
        pu3 = st.radio("b3", LIKERT_5, horizontal=True, key="pu3", label_visibility="collapsed")
        st.markdown('<div class="scale-anchors"><span>Strongly Disagree</span><span>Strongly Agree</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # C — Behavioural Intent
        st.markdown('<div class="section-header">After seeing this report, what is your most likely next step?</div>', unsafe_allow_html=True)
        intent = st.radio("intent", [
            "Reduce discretionary spending",
            "Seek cheaper housing",
            "Look for additional income",
            "No change planned",
        ], key="intent_val")

        st.markdown("---")
        lock = st.form_submit_button("🔒  SUBMIT & SEE MY RESULT")

    if lock:
        pu_composite = round((int(pu1) + int(pu2) + int(pu3)) / 3, 2)
        with st.spinner("Saving..."):
            sheet = connect_to_sheet()
            if sheet and st.session_state.get("target_row"):
                try:
                    r = st.session_state.target_row
                    # Col 8 (H) = POST_AITrust — using pu_composite as trust proxy
                    # Col 9 (I) = POST_PU_Composite
                    # Col 19 (S) = Behavioural Intent
                    # Cols 21–23 (U–W) = individual PU items
                    sheet.update([[pu_composite, pu_composite]], f"H{r}:I{r}")
                    sheet.update_cell(r, 19, intent)
                    sheet.update([[int(pu1), int(pu2), int(pu3)]], f"U{r}:W{r}")
                    st.session_state.final_score = st.session_state.res["score"]
                    st.session_state.last_id     = st.session_state.participant_id
                    st.session_state.step        = "finished"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save: {e}")
            elif not st.session_state.get("target_row"):
                st.error("⚠️ Row reference lost — please restart.")
            else:
                st.error("❌ Could not connect to sheet.")
