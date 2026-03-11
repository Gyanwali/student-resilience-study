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

/* ── Withdrawal notice box ── */
.withdrawal-box {
    background: var(--indigo-soft);
    border: 1.5px solid var(--indigo);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 1.2rem 0;
    font-size: 0.88rem;
    color: var(--text-body);
    line-height: 1.75;
}
.withdrawal-box b { color: var(--indigo); }
.withdrawal-box a {
    color: var(--indigo);
    font-weight: 700;
    text-decoration: underline;
}

/* ── Explain box (plain English insight under charts) ── */
.explain-box {
    background: var(--bg-subtle);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 0.8rem 0 1.6rem 0;
    font-size: 0.9rem;
    color: var(--text-body);
    line-height: 1.8;
}
.explain-box .explain-title {
    font-family: 'Playfair Display', serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 6px;
}
.explain-box .tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: 'Courier Prime', monospace;
    margin-right: 6px;
}
.tag-good    { background: #D1FAE5; color: #065F46; }
.tag-warn    { background: #FEF3C7; color: #92400E; }
.tag-risk    { background: #FEE2E2; color: #991B1B; }

/* ── Research gap advisory ── */
.gap-box {
    background: var(--amber-soft);
    border: 1.5px solid var(--amber);
    border-left: 5px solid var(--amber);
    border-radius: 10px;
    padding: 18px 22px;
    margin: 1.2rem 0;
    font-size: 0.88rem;
    color: var(--text-body);
    line-height: 1.8;
}
.gap-box b { color: var(--amber); }

/* ── Stat callout row ── */
.stat-row {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin: 1rem 0;
}
.stat-pill {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.stat-pill .sp-label { font-size: 0.8rem; color: var(--text-muted); font-weight: 500; }
.stat-pill .sp-value {
    font-family: 'Courier Prime', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
}

/* ── Conditional reveal ── */
.conditional-field {
    background: var(--teal-soft);
    border: 1.5px solid var(--teal);
    border-radius: 10px;
    padding: 16px 18px;
    margin-top: 10px;
}

/* ── Inline reassurance pill ── */
.reassure {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.74rem;
    color: var(--teal);
    background: var(--teal-soft);
    border: 1px solid var(--teal);
    border-radius: 20px;
    padding: 3px 10px;
    font-family: 'Courier Prime', monospace;
    font-weight: 700;
    margin-bottom: 8px;
}

/* ── Pulse glow on the locked score ring ── */
@keyframes pulse-ring {
    0%   { box-shadow: 0 0 0 0   rgba(244,63,94,0.35); }
    70%  { box-shadow: 0 0 0 16px rgba(244,63,94,0); }
    100% { box-shadow: 0 0 0 0   rgba(244,63,94,0); }
}
.pulse-ring {
    animation: pulse-ring 2s ease-out infinite;
}

/* ── Score-reveal lock gate ── */
.lock-gate {
    background: var(--bg-card);
    border: 2px solid var(--coral);
    border-radius: 18px;
    padding: 28px 24px;
    margin: 2rem 0 1.4rem 0;
    text-align: center;
    box-shadow: 0 4px 24px rgba(244,63,94,0.10);
}
.lock-gate .lg-eyebrow {
    font-family: 'Courier Prime', monospace;
    font-size: 0.7rem;
    color: var(--coral);
    text-transform: uppercase;
    letter-spacing: .2em;
    font-weight: 700;
    margin-bottom: 6px;
}
.lock-gate .lg-score-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 12px 0 8px 0;
}
.lock-gate .lg-ring {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    border: 4px solid var(--coral);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    filter: blur(6px);
    user-select: none;
}
.lock-gate .lg-ring-num {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    font-weight: 900;
    color: var(--coral);
    line-height: 1;
}
.lock-gate .lg-ring-lbl {
    font-size: 0.6rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: .08em;
}
.lock-gate .lg-lock-icon {
    font-size: 2rem;
    margin: 0 18px;
}
.lock-gate .lg-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 10px 0 6px 0;
}
.lock-gate .lg-sub {
    font-size: 0.88rem;
    color: var(--text-muted);
    line-height: 1.65;
    max-width: 380px;
    margin: 0 auto 14px auto;
}

/* ── Question progress dots ── */
.q-progress {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    margin-bottom: 1.4rem;
}
.q-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--border);
    transition: background .3s;
}
.q-dot.done   { background: var(--teal); }
.q-dot.active { background: var(--coral); transform: scale(1.3); }

/* ── Score-loading card (shown during calculation) ── */
@keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}
.loading-card {
    background: var(--bg-card);
    border: 1.5px solid var(--border);
    border-radius: 18px;
    padding: 40px 24px;
    text-align: center;
    margin: 2rem 0;
}
.loading-ring {
    width: 100px; height: 100px;
    border-radius: 50%;
    border: 4px solid var(--border);
    border-top: 4px solid var(--coral);
    margin: 0 auto 20px auto;
    animation: spin 1.2s linear infinite;
}
@keyframes spin {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.loading-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 6px;
}
.loading-sub {
    font-size: 0.88rem;
    color: var(--text-muted);
    line-height: 1.7;
}
.loading-steps {
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 20px;
    flex-wrap: wrap;
}
.loading-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    font-size: 0.76rem;
    color: var(--text-faint);
    font-family: 'Courier Prime', monospace;
}
.loading-step .ls-icon { font-size: 1.4rem; }

/* ── Form reassurance row ── */
.form-reassure-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: -4px 0 1rem 0;
    align-items: center;
}

/* ── Progress banner (inside results above post-survey) ── */
.unlock-banner {
    background: linear-gradient(135deg, var(--coral) 0%, #F97316 100%);
    border-radius: 14px;
    padding: 20px 24px;
    margin: 2rem 0 1.2rem 0;
    text-align: center;
    box-shadow: 0 6px 20px rgba(244,63,94,0.25);
}
.unlock-banner .ub-eyebrow {
    font-family: 'Courier Prime', monospace;
    font-size: 0.7rem;
    color: rgba(255,255,255,0.8);
    text-transform: uppercase;
    letter-spacing: .18em;
    margin-bottom: 5px;
    font-weight: 700;
}
.unlock-banner .ub-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
}
.unlock-banner .ub-sub {
    font-size: 0.85rem;
    color: rgba(255,255,255,0.85);
    line-height: 1.6;
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
    st.session_state.q_index        = 0   # tracks post-survey question progress


# ══════════════════════════════════════════════
# STEP: CALCULATING  — score reveal anticipation
# ══════════════════════════════════════════════
if st.session_state.step == "calculating":
    import time
    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step active"></div></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="loading-card">
        <div class="loading-ring"></div>
        <div class="loading-title">Analysing your financial profile…</div>
        <div class="loading-sub">
            Our AI is running your data through 5 research-backed models.<br>
            Your personalised resilience score is being calculated.
        </div>
        <div class="loading-steps">
            <div class="loading-step"><span class="ls-icon">🏠</span>Housing stress</div>
            <div class="loading-step"><span class="ls-icon">💰</span>Surplus ratio</div>
            <div class="loading-step"><span class="ls-icon">🛡️</span>Emergency buffer</div>
            <div class="loading-step"><span class="ls-icon">📚</span>Literacy score</div>
            <div class="loading-step"><span class="ls-icon">🍱</span>Food security</div>
        </div>
    </div>""", unsafe_allow_html=True)
    time.sleep(2.2)
    st.session_state.step = "results"
    st.rerun()


# ══════════════════════════════════════════════
# STEP: FINISHED  — personalised thank-you
# ══════════════════════════════════════════════
if st.session_state.step == "finished":
    score = st.session_state.get("final_score", 0)
    label, colour, insight = score_band(score)
    colour_map = {"Financially Resilient": "var(--green)", "Moderately Resilient": "var(--teal)", "Financially Vulnerable": "var(--coral)"}
    colour = colour_map.get(label, "var(--coral)")

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step done"></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="top-badge">✓ Complete — Here is Your Result</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Your Score<br>is <span class="accent">Revealed</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Based on your real financial data, analysed against 5 peer-reviewed frameworks.</div>', unsafe_allow_html=True)

    # Animated score ring — full reveal
    st.markdown(f"""
    <div style="text-align:center;margin:1.6rem 0 0.6rem 0">
        <div class="finish-score-ring pulse-ring" style="border-color:{colour};width:180px;height:180px;margin:0 auto 1rem auto">
            <span class="finish-score-num" style="color:{colour};font-size:3.6rem">{score}</span>
            <span class="finish-score-lbl">out of 100</span>
        </div>
        <div class="finish-band" style="color:{colour}">{label}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="finish-insight">{insight}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="finish-id">Your Participant ID: {st.session_state.get("last_id","—")}</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="withdrawal-box" style="margin-top:1.4rem">
        <b>🔒 Data Withdrawal Rights</b><br>
        You may request deletion of your data within <b>14 days</b> by emailing
        <a href="mailto:sandeepgyanwalli@gmail.com?subject=Data Withdrawal Request — {st.session_state.get('last_id','')}">sandeepgyanwalli@gmail.com</a>
        with the subject line <b>"Data Withdrawal Request"</b> and your Participant ID above.
        Your data will be permanently deleted within 14 days of your request.
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="analysis-box" style="margin-top:1rem;font-size:0.85rem;text-align:center">You may now safely close this window. Your data will be used solely for academic research on financial resilience among international students in Sydney.</div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════
# STEP: HOME
# ══════════════════════════════════════════════
if st.session_state.step == "home":
    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="top-badge">🎓 Free · Takes 3 Minutes · Sydney Students</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="hero-title">How financially<br>resilient are <span class="accent">you?</span></div>
    <div class="hero-sub">Get your personalised AI Financial Resilience Score — and finally understand where your money is going and what to do about it.</div>
    """, unsafe_allow_html=True)

    # ── Curiosity stat hook ─────────────────────────────────────────────
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:1.2rem 0 1.6rem 0">
        <div class="card" style="text-align:center;padding:18px 12px;border-top:4px solid var(--coral)">
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:900;color:var(--coral)">7 in 10</div>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:5px;line-height:1.4">international students in Sydney are in <b>housing stress</b></div>
        </div>
        <div class="card" style="text-align:center;padding:18px 12px;border-top:4px solid var(--amber)">
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:900;color:var(--amber)">1 in 3</div>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:5px;line-height:1.4">have skipped meals due to <b>lack of money</b></div>
        </div>
        <div class="card" style="text-align:center;padding:18px 12px;border-top:4px solid var(--teal)">
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:900;color:var(--teal)">&lt; 1 mo</div>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:5px;line-height:1.4">average emergency savings runway among students</div>
        </div>
    </div>
    <div style="font-size:0.72rem;color:var(--text-faint);margin-bottom:1.4rem;font-family:'Courier Prime',monospace">Sources: AHURI (2023), National Union of Students Australia (2022)</div>
    """, unsafe_allow_html=True)

    # ── Preview of what they'll get ─────────────────────────────────────
    st.markdown("""
    <div class="card" style="border:2px dashed var(--border);background:var(--bg-subtle)">
        <div class="section-header" style="margin-top:0">What you'll receive in 3 minutes</div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:8px">
            <div style="display:flex;align-items:flex-start;gap:10px">
                <span style="font-size:1.4rem">🎯</span>
                <div>
                    <div style="font-weight:700;font-size:0.9rem;color:var(--text-primary)">Your Resilience Score</div>
                    <div style="font-size:0.8rem;color:var(--text-muted)">A personalised score from 0–100 based on 5 research-backed factors</div>
                </div>
            </div>
            <div style="display:flex;align-items:flex-start;gap:10px">
                <span style="font-size:1.4rem">📊</span>
                <div>
                    <div style="font-weight:700;font-size:0.9rem;color:var(--text-primary)">Full Spending Breakdown</div>
                    <div style="font-size:0.8rem;color:var(--text-muted)">Charts showing exactly where your money goes vs. safe benchmarks</div>
                </div>
            </div>
            <div style="display:flex;align-items:flex-start;gap:10px">
                <span style="font-size:1.4rem">💰</span>
                <div>
                    <div style="font-weight:700;font-size:0.9rem;color:var(--text-primary)">Financial Runway</div>
                    <div style="font-size:0.8rem;color:var(--text-muted)">How many months your savings would last if income stopped</div>
                </div>
            </div>
            <div style="display:flex;align-items:flex-start;gap:10px">
                <span style="font-size:1.4rem">💡</span>
                <div>
                    <div style="font-weight:700;font-size:0.9rem;color:var(--text-primary)">Personalised Action Plan</div>
                    <div style="font-size:0.8rem;color:var(--text-muted)">Specific steps ranked by how much money they'd free up for you</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sample score card teaser ────────────────────────────────────────
    st.markdown("""
    <div class="card" style="margin-bottom:1.2rem">
        <div class="section-header" style="margin-top:0">Sample result — what yours will look like</div>
        <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap">
            <div style="text-align:center;min-width:100px">
                <div style="width:90px;height:90px;border-radius:50%;border:4px solid var(--coral);display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto">
                    <span style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:900;color:var(--coral);line-height:1">??</span>
                    <span style="font-size:0.6rem;color:var(--text-faint);text-transform:uppercase;letter-spacing:.08em">/ 100</span>
                </div>
                <div style="font-size:0.72rem;color:var(--text-muted);margin-top:8px;font-weight:600">Your Score</div>
            </div>
            <div style="flex:1;min-width:180px">
                <div style="margin-bottom:8px">
                    <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px">
                        <span style="color:var(--text-muted)">Housing</span><span style="color:var(--coral);font-weight:700">??%</span>
                    </div>
                    <div style="height:6px;background:var(--border);border-radius:3px"><div style="width:60%;height:6px;background:var(--coral)60;border-radius:3px"></div></div>
                </div>
                <div style="margin-bottom:8px">
                    <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px">
                        <span style="color:var(--text-muted)">Lifestyle</span><span style="color:var(--amber);font-weight:700">??%</span>
                    </div>
                    <div style="height:6px;background:var(--border);border-radius:3px"><div style="width:35%;height:6px;background:var(--amber)60;border-radius:3px"></div></div>
                </div>
                <div>
                    <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px">
                        <span style="color:var(--text-muted)">Emergency Runway</span><span style="color:var(--teal);font-weight:700">?? months</span>
                    </div>
                    <div style="height:6px;background:var(--border);border-radius:3px"><div style="width:45%;height:6px;background:var(--teal)60;border-radius:3px"></div></div>
                </div>
            </div>
        </div>
        <div style="font-size:0.78rem;color:var(--text-faint);margin-top:12px;font-style:italic">All data anonymised · Used for academic research only · University of New South Wales</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Consent ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="withdrawal-box">
        <b>🔒 Privacy & Your Rights</b> &nbsp;·&nbsp; All responses are anonymised.
        You may withdraw within <b>14 days</b> by emailing
        <a href="mailto:sandeepgyanwalli@gmail.com?subject=Data Withdrawal Request">sandeepgyanwalli@gmail.com</a>
        with your Participant ID (shown after you begin). Data deleted within 14 days of request.
    </div>""", unsafe_allow_html=True)

    consent = st.checkbox("✅  I consent to participate — my data will be anonymised and used for academic research only.")
    if consent:
        if st.button("🎯  See My Resilience Score →"):
            st.session_state.step = "pre_survey"
            st.rerun()


# ══════════════════════════════════════════════
# STEP: PRE-SURVEY  (1 question, before AI exposure)
# ══════════════════════════════════════════════
elif st.session_state.step == "pre_survey":
    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step active"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">YOUR ID · {st.session_state.participant_id} · keep this safe</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Quick<br><span class="accent">warm-up</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">One question before we dive in — it takes 5 seconds and helps us understand where you\'re starting from.</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="border-left:5px solid var(--amber);margin-bottom:0.5rem">
        <div style="font-size:0.72rem;color:var(--amber);font-family:'Courier Prime',monospace;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px">Before seeing your results</div>
        <div style="font-size:1.05rem;font-weight:600;color:var(--text-primary);line-height:1.5">
            How much do you currently trust AI tools to give useful advice on personal financial matters?
        </div>
    </div>""", unsafe_allow_html=True)

    with st.form("pre_form"):
        pre_trust = st.radio("pre_trust", [
            "1 — Not at all",
            "2 — Slightly",
            "3 — Neutral",
            "4 — Mostly",
            "5 — Completely"
        ], horizontal=False, key="pre_trust_val", label_visibility="collapsed")
        st.markdown("---")
        go = st.form_submit_button("Continue — Build My Profile  →")

    if go:
        # Map label back to integer
        val_map = {"1 — Not at all": 1, "2 — Slightly": 2, "3 — Neutral": 3, "4 — Mostly": 4, "5 — Completely": 5}
        st.session_state.pre_ai_trust = val_map.get(pre_trust, 3)
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
    st.markdown(f'<div class="pid-chip">YOUR ID · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Build your<br><span class="accent">profile</span></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="explain-box" style="margin-bottom:1.4rem">
        <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:1.8rem">⚡</span>
            <div>
                <div style="font-weight:700;font-size:0.95rem;color:var(--text-primary)">Your score is calculated instantly — no waiting.</div>
                <div style="font-size:0.85rem;color:var(--text-muted);margin-top:3px">Enter approximate figures — estimates are fine. All data is anonymised.</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── RESEARCH GAP NOTE (visible only in dev / can remove before deployment) ──
    # Missing covariates: age group, gender, nationality, study level, weekly work hours
    # These are standard in international student financial resilience literature.
    # Adding them here improves your regression model's explanatory power significantly.

    # ── Family support toggle OUTSIDE form so it renders conditionally ────────
    st.markdown('<div class="section-header">Income & Family Support</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-reassure-row"><span class="reassure">🔒 Never shared</span><span class="reassure">✓ Estimates are fine</span><span class="reassure">✓ Anonymised instantly</span></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        inc = st.number_input("Monthly Income from Work (AUD $)", min_value=0, max_value=15000, value=3200, step=50, key="inc_outer")
    with col_b:
        p_supp = st.radio("Receiving Family Financial Support?", ["No", "Yes"], horizontal=True, key="p_supp_outer")

    p_amt = 0
    if p_supp == "Yes":
        st.markdown('<div class="conditional-field">', unsafe_allow_html=True)
        p_amt = st.number_input("💚 How much family support do you receive per month? (AUD $)",
                                 min_value=50, max_value=5000, value=500, step=50, key="p_amt_outer")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Demographics</div>', unsafe_allow_html=True)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        age_group = st.selectbox("Age Group", ["18–22", "23–26", "27–30", "31+"], key="age_outer")
    with col_d2:
        study_level = st.selectbox("Study Level", ["Undergraduate", "Postgraduate (Coursework)", "Postgraduate (Research)", "Other"], key="study_outer")

    col_d3, col_d4 = st.columns(2)
    with col_d3:
        gender = st.selectbox("Gender", ["Male", "Female", "Non-binary / Other", "Prefer not to say"], key="gender_outer")
    with col_d4:
        work_hrs = st.number_input("Weekly Work Hours", min_value=0, max_value=60, value=20, step=1, key="work_outer")

    with st.form("input_form"):
        st.markdown('<div class="section-header">Location</div>', unsafe_allow_html=True)
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield",
                           "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
        addr       = st.selectbox("Suburb of Residence", suburbs)
        custom_sub = st.text_input("If 'Other', please specify:", placeholder="e.g. Chatswood")
        final_addr = custom_sub.strip() if addr == "Other" else addr

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

        st.markdown('<div class="section-header">Financial Knowledge</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            lit    = st.select_slider("Financial Literacy Level", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        with col2:
            months = st.number_input("Months Living in Sydney", min_value=1, max_value=120, value=12)

        meals = st.radio("Have you skipped meals due to lack of money in the past month?", ["No", "Yes"], horizontal=True)

        st.markdown("---")
        st.markdown('<div style="font-size:0.82rem;color:var(--text-muted);text-align:center;margin-bottom:10px">🔒 Your data is anonymised · Used for academic research only</div>', unsafe_allow_html=True)
        submitted = st.form_submit_button("⚡  Calculate My Resilience Score  →", use_container_width=True)

    if submitted:
        if addr == "Other" and not final_addr:
            st.warning("Please specify your suburb.")
        else:
            # Pull family support values captured OUTSIDE the form
            inc    = st.session_state.get("inc_outer", 3200)
            p_supp = st.session_state.get("p_supp_outer", "No")
            p_amt  = st.session_state.get("p_amt_outer", 0) if p_supp == "Yes" else 0
            age_group   = st.session_state.get("age_outer", "23–26")
            study_level = st.session_state.get("study_outer", "Undergraduate")
            gender      = st.session_state.get("gender_outer", "Prefer not to say")
            work_hrs    = st.session_state.get("work_outer", 20)

            data = {
                "income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit,
                "rent": rent, "uber": uber, "groc": groc, "trans": trans,
                "bills": bills, "meals": meals, "addr": final_addr,
                "savings": savings, "lit": lit, "months": months,
                "age": age_group, "study": study_level,
                "gender": gender, "work_hrs": work_hrs,
            }
            res = run_model(data)
            st.session_state.data = data
            st.session_state.res  = res

            with st.spinner("🔬 Analysing your financial profile across 5 research dimensions..."):
                import time; time.sleep(0.8)  # Brief pause for UX anticipation
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

            st.session_state.step = "calculating"
            st.rerun()


# ══════════════════════════════════════════════
# STEP: RESULTS
# ══════════════════════════════════════════════
elif st.session_state.step == "results":
    ai   = st.session_state.res
    data = st.session_state.data

    st.markdown('<div class="step-bar"><div class="step done"></div><div class="step done"></div><div class="step done"></div><div class="step active"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">YOUR ID · {st.session_state.participant_id}</div>', unsafe_allow_html=True)

    # Lead with the score band for immediate impact
    band_label = "Financially Resilient 🟢" if ai['score']>=65 else "Moderately Resilient 🟡" if ai['score']>=40 else "Financially Vulnerable 🔴"
    band_col   = "var(--green)" if ai['score']>=65 else "var(--amber)" if ai['score']>=40 else "var(--coral)"
    st.markdown(f"""
    <div style="margin-bottom:0.3rem">
        <div class="hero-title" style="margin-bottom:0.2rem">Your score: <span style="color:{band_col}">{ai['score']}</span><span style="font-size:1.8rem;color:var(--text-muted)">/100</span></div>
        <div style="font-family:'Playfair Display',serif;font-size:1.2rem;font-weight:700;color:{band_col};margin-bottom:0.8rem">{band_label}</div>
    </div>""", unsafe_allow_html=True)

    surplus_display = f"+${ai['surplus']:,.0f}" if ai['surplus'] >= 0 else f"-${abs(ai['surplus']):,.0f}"

    # ── 3 headline metrics ─────────────────────────────────────────────────
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card metric-card-1">
            <span class="metric-value" style="color:var(--coral)">{ai['score']}</span>
            <div class="metric-label">Resilience Score / 100</div>
        </div>
        <div class="metric-card metric-card-2">
            <span class="metric-value" style="color:var(--teal)">{ai['runway']}</span>
            <div class="metric-label">Financial Runway (months)</div>
        </div>
        <div class="metric-card metric-card-3">
            <span class="metric-value" style="color:var(--amber)">{ai['prob']}%</span>
            <div class="metric-label">Stability Probability</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Plain-English metric explanation ──────────────────────────────────
    score_band_label = "Financially Resilient 🟢" if ai['score']>=65 else "Moderately Resilient 🟡" if ai['score']>=40 else "Financially Vulnerable 🔴"
    score_colour     = "var(--green)" if ai['score']>=65 else "var(--amber)" if ai['score']>=40 else "var(--coral)"
    runway_status    = "✅ Safe" if ai['runway']>=3 else "⚠️ Low — below 3-month minimum" if ai['runway']>=1 else "🔴 Critical — under 1 month"
    surplus_status   = f"✅ You have ${ai['surplus']:,.0f} left each month after all expenses." if ai['surplus']>=0 else f"🔴 You are spending ${abs(ai['surplus']):,.0f} more than you earn each month."

    st.markdown(f"""
    <div class="explain-box">
        <div class="explain-title">What do these numbers mean?</div>
        <b>Resilience Score ({ai['score']}/100):</b> This is your overall financial health rating, calculated from five research-backed factors.
        You fall into the <span style="color:{score_colour};font-weight:700">{score_band_label}</span> band.<br><br>
        <b>Financial Runway ({ai['runway']} months):</b> If your income stopped today, your savings would last
        <b>{ai['runway']} months</b>. Status: {runway_status}.<br><br>
        <b>Stability Probability ({ai['prob']}%):</b> Based on your income-to-expense ratio, there is a
        <b>{ai['prob']}% chance</b> of remaining financially stable. Above 60% is considered stable.<br><br>
        <b>Monthly Cash Flow:</b> {surplus_status}
    </div>""", unsafe_allow_html=True)

    # ── Risk flag box ──────────────────────────────────────────────────────
    flags_html = "".join(f"<li style='margin:8px 0'>{f}</li>" for f in ai['flags']) \
                 if ai['flags'] else "<li>✅ No critical stress indicators detected — your profile is within safe thresholds.</li>"
    st.markdown(f"""
    <div class="analysis-box">
        <b>🤖 AI Risk Assessment — {data['addr']}</b><br><br>
        Housing takes up <span class="highlight">{ai['rent_pct']:.1f}%</span> of your income
        and lifestyle spending accounts for <span class="highlight-teal">{ai['uber_pct']:.1f}%</span>.
        Your monthly cash flow is <span class="highlight">{surplus_display}</span> with a savings runway of
        <span class="highlight-amber">{ai['runway']} months</span>.<br><br>
        <b>⚠️ Flags Detected:</b>
        <ul style="margin:10px 0 0 0;padding-left:20px;color:var(--text-body)">{flags_html}</ul>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊  Spending", "📈  Benchmarks", "🔬  Score Logic", "💡  Recommendations"])

    # ════════════════════════════════════════════
    # TAB 1 — SPENDING
    # ════════════════════════════════════════════
    with tab1:
        # Donut pie ────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">Where does your money go each month?</div>', unsafe_allow_html=True)
        fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()),
                         hole=0.55, color_discrete_sequence=COLORS)
        fig_pie.update_layout(**CHART_LAYOUT, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)))
        fig_pie.update_traces(textposition="inside", textfont_size=11,
                              marker=dict(line=dict(color="rgba(0,0,0,0)", width=0)))
        st.plotly_chart(fig_pie, use_container_width=True)

        biggest_cat = max(ai['exp_breakdown'], key=ai['exp_breakdown'].get)
        biggest_val = ai['exp_breakdown'][biggest_cat]
        biggest_pct = round(biggest_val / max(ai['m_inc'],1) * 100, 1)
        st.markdown(f"""
        <div class="explain-box">
            <div class="explain-title">💡 Reading the Spending Pie</div>
            Each slice shows one spending category as a share of your total monthly expenses of <b>${ai['m_exp']:,.0f}</b>.
            Your single largest expense is <b>{biggest_cat}</b> at <b>${biggest_val:,.0f}/month ({biggest_pct}% of income)</b>.
            A healthy budget keeps housing below <b>30%</b> and lifestyle below <b>15%</b> of income.
            Slices that feel oversized are your best opportunities to free up money.
        </div>""", unsafe_allow_html=True)

        # Income vs Expenses bar ──────────────────────────────────────────
        st.markdown('<div class="section-header">Income vs. Total Expenses vs. Surplus</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        bar_vals = [ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)]
        fig_bar.add_trace(go.Bar(
            x=["💚 Total Income", "🔴 Total Expenses", "🟡 Monthly Surplus"],
            y=bar_vals,
            marker_color=["#10B981", "#F43F5E", "#F59E0B"],
            marker_line=dict(color="rgba(0,0,0,0)", width=0),
            text=[f"${v:,.0f}" for v in bar_vals],
            textposition="outside", textfont=dict(color="var(--text-body)", size=13),
        ))
        fig_bar.update_layout(**CHART_LAYOUT,
            yaxis=dict(showgrid=False, showticklabels=False),
            xaxis=dict(showgrid=False, tickfont=dict(size=12)),
            showlegend=False, height=300)
        st.plotly_chart(fig_bar, use_container_width=True)

        bar_msg = (f"After all your expenses, you have <b>${ai['surplus']:,.0f} left over each month</b> — this is your monthly surplus. Every dollar of this surplus can go toward building your emergency fund."
                   if ai['surplus'] >= 0 else
                   f"Your expenses <b>exceed your income by ${abs(ai['surplus']):,.0f}/month</b>. You are going backwards — this needs urgent attention.")
        st.markdown(f"""
        <div class="explain-box">
            <div class="explain-title">💡 What This Bar Chart Shows</div>
            The <b style="color:#10B981">green bar</b> is your total income (${ai['m_inc']:,.0f}/month including any family support),
            the <b style="color:#F43F5E">red bar</b> is everything you spend (${ai['m_exp']:,.0f}/month),
            and the <b style="color:#F59E0B">amber bar</b> is what remains. {bar_msg}
        </div>""", unsafe_allow_html=True)

        # Horizontal % bars ───────────────────────────────────────────────
        st.markdown('<div class="section-header">Each expense as a % of your income</div>', unsafe_allow_html=True)
        cats     = list(ai['exp_breakdown'].keys())
        pct_vals = [round(v / max(ai['m_inc'],1) * 100, 1) for v in ai['exp_breakdown'].values()]
        fig_h = go.Figure(go.Bar(
            x=pct_vals, y=cats, orientation='h',
            marker=dict(color=COLORS[:len(cats)], line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[f"{p}% (${v:,.0f})" for p, v in zip(pct_vals, ai['exp_breakdown'].values())],
            textposition="outside",
        ))
        fig_h.update_layout(**CHART_LAYOUT,
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, max(pct_vals)*1.4]),
            yaxis=dict(showgrid=False, tickfont=dict(size=12)),
            showlegend=False, height=300)
        st.plotly_chart(fig_h, use_container_width=True)

        other_pct = round(sum(pct_vals) - ai['rent_pct'], 1)
        st.markdown(f"""
        <div class="explain-box">
            <div class="explain-title">💡 Why Percentages Matter</div>
            Percentages let you compare your spending fairly regardless of income level.
            Your housing alone is <b>{ai['rent_pct']:.1f}%</b> of income
            and all other expenses total <b>{other_pct}%</b>.
            Key thresholds: <b>Housing ≤ 30%</b> (AHURI 2023) · <b>Lifestyle ≤ 15%</b> · <b>Groceries 10–18%</b> · <b>Transport ≤ 12%</b>.
            Any bar significantly longer than those targets is costing you financial resilience.
        </div>""", unsafe_allow_html=True)

        # 4-stat summary row ──────────────────────────────────────────────
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:1rem 0">
            <div class="card" style="padding:14px 18px">
                <div style="font-size:0.72rem;color:var(--text-faint);font-family:'Courier Prime',monospace;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">Monthly Income</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--green)">${ai['m_inc']:,.0f}</div>
            </div>
            <div class="card" style="padding:14px 18px">
                <div style="font-size:0.72rem;color:var(--text-faint);font-family:'Courier Prime',monospace;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">Monthly Expenses</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--coral)">${ai['m_exp']:,.0f}</div>
            </div>
            <div class="card" style="padding:14px 18px">
                <div style="font-size:0.72rem;color:var(--text-faint);font-family:'Courier Prime',monospace;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">Monthly Surplus</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:{'var(--green)' if ai['surplus']>=0 else 'var(--red)'}">{surplus_display}</div>
            </div>
            <div class="card" style="padding:14px 18px">
                <div style="font-size:0.72rem;color:var(--text-faint);font-family:'Courier Prime',monospace;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">Savings Rate</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--indigo)">{ai['save_rate']}%</div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════
    # TAB 2 — BENCHMARKS
    # ════════════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-header">How you compare to research benchmarks</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="explain-box">
            <div class="explain-title">📏 What Are Benchmarks?</div>
            These are spending thresholds drawn from Australian and international financial research.
            <span class="tag tag-good">On Track</span> means you are within the safe range.
            <span class="tag tag-risk">Over</span> means you are above the recommended ceiling — an area to cut.
            <span class="tag tag-warn">Under</span> means spending less than typical (usually fine, except for savings rate where higher is better).
            The <b>dark line</b> marks exactly where you sit.
        </div>""", unsafe_allow_html=True)

        benchmarks = [
            ("🏠 Housing % of Income",       ai['rent_pct'],  25, 30, "%",
             "If your housing exceeds 30% of income you are classified as being in 'housing stress' (AHURI, 2023). This is the biggest financial burden for international students in Sydney."),
            ("🍔 Lifestyle & Eating Out",     ai['uber_pct'],  10, 15, "%",
             "Uber Eats, restaurants, entertainment. Above 15% means lifestyle is competing with your savings goals."),
            ("🛒 Groceries",                  ai['groc_pct'],  10, 18, "%",
             "10–18% of income on groceries is typical for Sydney. Below 10% may indicate you are cutting food — a food security risk."),
            ("🚌 Transport",                  ai['trans_pct'],  5, 12, "%",
             "Public transport should sit around 5–8% of income. Above 12% suggests heavy rideshare or car dependency."),
            ("💰 Monthly Savings Rate",       ai['save_rate'],  20, 30, "%",
             "Ideally save 20–30% of income monthly. This is what builds your emergency runway and long-term security."),
        ]
        for label, val, lo, hi, unit, explanation in benchmarks:
            if lo <= val <= hi:
                bar_col, tag_cls, tag_txt = "#10B981", "tag-good", "On Track ✅"
            elif val < lo:
                bar_col, tag_cls, tag_txt = "#6366F1", "tag-warn", "Under ↓"
            else:
                bar_col, tag_cls, tag_txt = "#F43F5E", "tag-risk", "Over ⚠️"
            pct_w = min(val / 50 * 100, 100)
            st.markdown(f"""
            <div class="card" style="margin-bottom:12px;padding:16px 20px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <span style="font-weight:600;font-size:0.92rem;color:var(--text-primary)">{label}</span>
                    <span>
                        <span style="font-family:'Courier Prime',monospace;font-weight:700;color:{bar_col};font-size:1.05rem">{val}{unit}</span>
                        &nbsp;<span class="tag {tag_cls}">{tag_txt}</span>
                    </span>
                </div>
                <div style="font-size:0.76rem;color:var(--text-faint);margin-bottom:10px">Target range: {lo}–{hi}{unit}</div>
                <div class="bench-track">
                    <div class="bench-fill" style="width:{pct_w:.0f}%;background:{bar_col}60"></div>
                    <div class="bench-marker" style="left:{min(pct_w,97):.0f}%;background:{bar_col}"></div>
                </div>
                <div style="font-size:0.83rem;color:var(--text-muted);margin-top:10px;line-height:1.6">{explanation}</div>
            </div>""", unsafe_allow_html=True)

        # Radar chart ─────────────────────────────────────────────────────
        st.markdown('<div class="section-header">Full spending profile radar</div>', unsafe_allow_html=True)
        rcats = ["Housing", "Groceries", "Lifestyle", "Transport", "Bills", "Remittance"]
        rvals = [ai['rent_pct'], ai['groc_pct'], ai['uber_pct'], ai['trans_pct'],
                 round(float(data['bills']) / max(ai['m_inc'],1) * 100, 1),
                 round(float(data['remit']) / max(ai['m_inc'],1) * 100, 1)]
        bvals = [28, 14, 12, 8, 5, 5]
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(r=bvals+[bvals[0]], theta=rcats+[rcats[0]], fill='toself',
            name='Benchmark Zone', line=dict(color='#10B981', dash='dash', width=2), fillcolor='rgba(16,185,129,0.08)'))
        fig_r.add_trace(go.Scatterpolar(r=rvals+[rvals[0]], theta=rcats+[rcats[0]], fill='toself',
            name='Your Profile', line=dict(color='#F43F5E', width=2.5), fillcolor='rgba(244,63,94,0.12)'))
        fig_r.update_layout(**CHART_LAYOUT,
            polar=dict(bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0,50], gridcolor='rgba(160,160,160,0.2)', color='var(--text-faint)'),
                angularaxis=dict(gridcolor='rgba(160,160,160,0.2)', tickfont=dict(size=11))),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)), height=400)
        st.plotly_chart(fig_r, use_container_width=True)

        over_cats = [rcats[i] for i, v in enumerate(rvals) if v > bvals[i]]
        st.markdown(f"""
        <div class="explain-box">
            <div class="explain-title">💡 How to Read the Radar</div>
            The <b style="color:#10B981">green dashed shape</b> is the ideal spending profile — the "benchmark zone".
            The <b style="color:#F43F5E">red filled shape</b> is your actual profile.
            Anywhere your red shape <b>bulges outside the green</b> is where you are overspending relative to the benchmark.<br><br>
            {"Your highest-priority areas to address: <b>" + ", ".join(over_cats) + "</b>." if over_cats else "✅ Your profile fits well within the benchmark zone across all categories — well balanced."}
        </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════
    # TAB 3 — SCORE LOGIC
    # ════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-header">How your resilience score was built</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="explain-box">
            <div class="explain-title">🔬 The 5-Component Framework</div>
            Your score is not a simple rule-of-thumb — it is built from five independent dimensions,
            each grounded in a peer-reviewed academic source. Each component contributes a different
            maximum number of points to the 100-point total. The waterfall chart below shows exactly
            how each component stacked up to reach your final score.
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class="formula-box">
            <span class="f1">C1 · Surplus Ratio    (max 35 pts)</span><span class="cite">  — Carroll (1997) · Are you earning more than you spend?</span><br>
            <span class="f2">C2 · Housing Stress   (max 25 pts)</span><span class="cite">  — AHURI (2023)   · Is rent below 30% of income?</span><br>
            <span class="f3">C3 · Emergency Buffer (max 20 pts)</span><span class="cite">  — Deaton (1991)  · Do you have ≥3 months of savings?</span><br>
            <span class="f1">C4 · Fin. Literacy    (max 10 pts)</span><span class="cite">  — Lusardi & Mitchell (2014) · Self-reported knowledge level</span><br>
            <span class="f2">C5 · Food Security    (max 10 pts)</span><span class="cite">  — Gundersen & Ziliak (2015) · No meal-skipping = 10 pts</span>
        </div>""", unsafe_allow_html=True)

        # Waterfall chart ─────────────────────────────────────────────────
        comps = ai['score_components']
        vals  = list(comps.values())
        total = sum(vals)
        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"]*len(vals)+["total"],
            x=list(comps.keys())+["Final Score"], y=vals+[total],
            connector=dict(line=dict(color="rgba(160,160,160,0.3)", width=1)),
            increasing=dict(marker_color="#10B981"), decreasing=dict(marker_color="#F43F5E"),
            totals=dict(marker_color="#6366F1"),
            text=[f"{v:+.1f} pts" for v in vals]+[f"{total} / 100"],
            textposition="outside", textfont=dict(size=11),
        ))
        fig_wf.update_layout(**CHART_LAYOUT,
            yaxis=dict(showgrid=False, range=[0, max(total,100)+22]),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            showlegend=False, height=380)
        st.plotly_chart(fig_wf, use_container_width=True)

        st.markdown(f"""
        <div class="explain-box">
            <div class="explain-title">💡 Reading the Waterfall Chart</div>
            Each <b style="color:#10B981">green bar</b> is a component that added points to your score.
            Each <b style="color:#F43F5E">red bar</b> would represent a component that added 0 (no negative points — the minimum per component is 0).
            The <b style="color:#6366F1">purple bar</b> on the right is your final total of <b>{total}/100</b>.
            The tallest green bars are your financial strengths — the shortest (or absent) ones are your improvement opportunities.
        </div>""", unsafe_allow_html=True)

        # Per-component breakdown cards ───────────────────────────────────
        st.markdown('<div class="section-header">Component-by-component breakdown</div>', unsafe_allow_html=True)
        maxes = {"Surplus Ratio": 35, "Housing Stress": 25, "Emerg. Buffer": 20, "Fin. Literacy": 10, "Food Security": 10}
        comp_notes = {
            "Surplus Ratio":  f"Your income surplus is {'positive' if ai['surplus']>=0 else 'negative'} at {surplus_display}/month. {'Strong foundation.' if ai['surplus']>=0 else 'This is your most urgent issue.'}",
            "Housing Stress": f"Rent is {ai['rent_pct']:.1f}% of income. {'Below 30% — no housing stress.' if ai['rent_pct']<=30 else 'Above 30% — you are in housing stress.'}",
            "Emerg. Buffer":  f"Your savings cover {ai['runway']} months of expenses. {'Good buffer.' if ai['runway']>=3 else 'Below the 3-month minimum.'}",
            "Fin. Literacy":  f"Self-reported as {data['lit']}. Higher literacy strongly predicts better financial outcomes (Lusardi & Mitchell, 2014).",
            "Food Security":  f"{'No meal-skipping recorded — full 10 points.' if data['meals']=='No' else 'Meal-skipping detected — 0 points. This is a critical stress indicator.'}",
        }
        for comp, score_val in comps.items():
            max_val   = maxes.get(comp, 10)
            bar_pct   = round(score_val / max_val * 100)
            bar_col   = "#10B981" if bar_pct >= 60 else "#F59E0B" if bar_pct >= 30 else "#F43F5E"
            st.markdown(f"""
            <div class="card" style="margin-bottom:10px;padding:16px 20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                    <span style="font-weight:700;font-size:0.95rem;color:var(--text-primary)">{comp}</span>
                    <span style="font-family:'Courier Prime',monospace;font-weight:700;font-size:1rem;color:{bar_col}">{score_val} / {max_val} pts</span>
                </div>
                <div class="bench-track" style="height:8px;margin-bottom:10px">
                    <div class="bench-fill" style="width:{bar_pct}%;background:{bar_col};height:8px"></div>
                </div>
                <div style="font-size:0.84rem;color:var(--text-muted);line-height:1.6">{comp_notes.get(comp,'')}</div>
            </div>""", unsafe_allow_html=True)

        sc  = "var(--green)" if ai['score']>=65 else "var(--amber)" if ai['score']>=40 else "var(--coral)"
        lc  = "Strong" if ai['score']>=65 else "Moderate" if ai['score']>=40 else "Vulnerable"
        st.markdown(f"""
        <div class="insight-grid">
            <div class="insight-card">
                <div class="i-label">Final Score</div>
                <div class="i-value" style="color:{sc}">{ai['score']}/100</div>
                <div class="i-sub">Band: {lc}</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Monthly Surplus</div>
                <div class="i-value" style="color:{'var(--green)' if ai['surplus']>=0 else 'var(--red)'}">{surplus_display}</div>
                <div class="i-sub">Income minus all expenses</div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════
    # TAB 4 — RECOMMENDATIONS
    # ════════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-header">Personalised action plan</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="explain-box">
            <div class="explain-title">💡 These Are Specific to Your Data</div>
            Every recommendation below was generated directly from the numbers you entered — not generic advice.
            They are ordered by financial impact. Focus on the first one first.
        </div>""", unsafe_allow_html=True)

        recs = []
        if ai['surplus'] < 0:
            recs.append(("⚡ URGENT — Monthly Deficit", "var(--coral)",
                         f"You are spending <b>${abs(ai['surplus']):,.0f} more than you earn every month</b>. This is unsustainable. Contact your university's Financial Hardship Office this week — emergency grants, interest-free loans, and fee-deferral options may be available to you right now."))
        if ai['rent_pct'] > 30:
            saving = round((ai['rent_pct'] - 28) / 100 * ai['m_inc'])
            recs.append(("🏠 Housing Stress", "var(--coral)",
                         f"Your rent is <b>{ai['rent_pct']:.1f}% of income</b> — above the AHURI 30% stress threshold. Moving to shared accommodation in Auburn, Parramatta or Strathfield could save you approximately <b>${saving}/month</b> and directly improve your resilience score."))
        if ai['uber_pct'] > 15:
            saving = round(float(data['uber']) * 4.33 * 0.4)
            recs.append(("🍔 Discretionary Spending", "var(--amber)",
                         f"Cutting Uber Eats and eating-out by 40% would free <b>~${saving}/month</b>. Meal prepping just 4 days a week is the single highest-impact behavioural change you can make right now — it costs less and builds a healthy habit."))
        if ai['runway'] < 3:
            monthly_needed = round((ai['m_exp'] * 3 - float(data['savings'])) / 12)
            recs.append(("💰 Build Your Emergency Buffer", "var(--teal)",
                         f"You have <b>{ai['runway']} months</b> of savings runway — the research minimum is 3 months (Deaton, 1991). Saving an extra <b>${max(monthly_needed,50):,}/month</b> would get you to the 3-month target within 12 months."))
        if float(data['remit']) > ai['m_inc'] * 0.15:
            fee_save = round(float(data['remit']) * 0.025)
            recs.append(("💸 Reduce Remittance Fees", "var(--indigo)",
                         f"You are sending <b>{ai['remit_pct']:.1f}% of income</b> overseas — above the World Bank's 15% guideline. Switching from bank transfers to <b>Wise or Remitly</b> (typically 0.5–1.5% fees vs. 3–5% for banks) could save you <b>~${fee_save}/month</b> in fees alone."))
        if data['meals'] == "Yes":
            recs.append(("🍱 Food Security — Act Now", "var(--coral)",
                         "Meal-skipping is one of the most critical stress indicators in this research (Gundersen & Ziliak, 2015). <b>Free meals</b> are available at your university student hub. <b>OzHarvest</b> and <b>Foodbank NSW</b> also provide emergency food support — no questions asked, no cost."))
        if data.get('lit') == "Novice":
            recs.append(("📚 Improve Financial Literacy", "var(--teal)",
                         "Financial literacy directly predicts better money outcomes. Free resources: <b>ASIC MoneySmart</b> (moneysmart.gov.au), your university financial counsellor, and <b>Student Edge</b> for student-specific discounts and budgeting tools."))
        if not recs:
            recs.append(("✅ You Are On Track", "var(--green)",
                         "No critical stress points in your profile. To keep improving: maintain your surplus, push your savings rate toward 25%, and build your emergency buffer toward 6 months."))

        for i, (title, accent, body) in enumerate(recs):
            priority_badge = '<span style="font-size:0.65rem;font-family:\'Courier Prime\',monospace;color:var(--coral);margin-left:8px">● HIGHEST PRIORITY</span>' if i == 0 and len(recs) > 1 else ""
            st.markdown(f"""
            <div class="rec-card" style="border-left-color:{accent}">
                <div class="rec-title" style="color:{accent}">{title}{priority_badge}</div>
                <div class="rec-body">{body}</div>
            </div>""", unsafe_allow_html=True)

        # Savings projection ──────────────────────────────────────────────
        st.markdown('<div class="section-header">12-Month Savings Projection</div>', unsafe_allow_html=True)
        mths      = list(range(0, 13))
        cur_sav   = float(data['savings'])
        m_add     = max(ai['surplus'], 0)
        target_3  = ai['m_exp'] * 3
        fig_proj  = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=mths, y=[cur_sav + m_add*m for m in mths],
            name="Current trajectory",
            line=dict(color="#6366F1", width=2.5),
            fill='tozeroy', fillcolor='rgba(99,102,241,0.07)'))
        fig_proj.add_trace(go.Scatter(
            x=mths, y=[cur_sav + m_add*1.2*m for m in mths],
            name="If 20% more saved",
            line=dict(color="#10B981", width=2, dash='dash')))
        fig_proj.add_hline(y=target_3, line_dash="dot", line_color="#F43F5E",
            annotation_text=f"3-month target: ${target_3:,.0f}",
            annotation_position="top right",
            annotation_font=dict(color="#F43F5E", size=11))
        fig_proj.update_layout(**CHART_LAYOUT,
            xaxis=dict(title="Month", showgrid=False),
            yaxis=dict(title="Total Savings (AUD $)", showgrid=False),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)), height=320)
        st.plotly_chart(fig_proj, use_container_width=True)

        proj_12   = cur_sav + m_add * 12
        gap       = target_3 - proj_12
        proj_msg  = (f"At your current savings rate, you will reach <b>${proj_12:,.0f}</b> in 12 months — <b>above the 3-month target of ${target_3:,.0f}</b>. ✅"
                     if gap <= 0 else
                     f"At your current rate, you will reach <b>${proj_12:,.0f}</b> in 12 months — still <b>${gap:,.0f} short</b> of the 3-month target. Saving an extra <b>${round(gap/12):,}/month</b> closes that gap exactly in 12 months.")
        st.markdown(f"""
        <div class="explain-box">
            <div class="explain-title">💡 Reading Your Savings Projection</div>
            The <b style="color:#6366F1">purple line</b> is your savings trajectory if you continue at current behaviour.
            The <b style="color:#10B981">green dashed line</b> shows the impact of saving just 20% more each month.
            The <b style="color:#F43F5E">red dotted line</b> is your 3-month emergency buffer target (${target_3:,.0f}).<br><br>
            {proj_msg}
        </div>""", unsafe_allow_html=True)

    # ── POST-SURVEY  — lock gate + progress dots ──────────────────────────────
    st.markdown("---")

    # Blurred score teaser — creates urgency to complete the survey
    sc_col_gate = "var(--green)" if ai['score']>=65 else "var(--amber)" if ai['score']>=40 else "var(--coral)"
    st.markdown(f"""
    <div class="lock-gate">
        <div class="lg-eyebrow">🔒 Your result is ready — one last step</div>
        <div class="lg-score-wrap">
            <div class="lg-ring pulse-ring">
                <div class="lg-ring-num" style="color:{sc_col_gate}">{ai['score']}</div>
                <div class="lg-ring-lbl">/ 100</div>
            </div>
            <div class="lg-lock-icon">🔐</div>
        </div>
        <div class="lg-title">Your Resilience Score is hidden above</div>
        <div class="lg-sub">
            Answer 4 quick questions about the AI report you just read —
            then your full result is permanently saved and revealed.
            Takes <b>30 seconds</b>.
        </div>
    </div>""", unsafe_allow_html=True)

    # Progress dots
    if "q_done" not in st.session_state:
        st.session_state.q_done = 0

    def _dots(n_done, total=4):
        dots = ""
        for i in range(total):
            if i < n_done:   cls = "q-dot done"
            elif i == n_done: cls = "q-dot active"
            else:             cls = "q-dot"
            dots += f'<div class="{cls}"></div>'
        label = f"Question {min(n_done+1,total)} of {total}"
        return f'<div class="q-progress">{dots}</div><div style="text-align:center;font-size:0.76rem;color:var(--text-faint);font-family:\'Courier Prime\',monospace;font-weight:700;margin-bottom:1.2rem">{label}</div>'

    st.markdown(_dots(0), unsafe_allow_html=True)

    with st.form("post_form"):

        # B1 — PU Understanding
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">This AI report improved my understanding of my financial situation.</div>
            <span class="scale-cite">Perceived Usefulness — Davis (1989) · Question 1 of 4</span>
        </div>""", unsafe_allow_html=True)
        pu1 = st.radio("Rate B1", ["1 — Strongly Disagree", "2", "3 — Neutral", "4", "5 — Strongly Agree"],
                        horizontal=True, key="pu1", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(_dots(1), unsafe_allow_html=True)

        # B2 — PU Useful
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">This AI report is useful for managing my finances as a student in Sydney.</div>
            <span class="scale-cite">Perceived Usefulness — Davis (1989) · Question 2 of 4</span>
        </div>""", unsafe_allow_html=True)
        pu2 = st.radio("Rate B2", ["1 — Strongly Disagree", "2", "3 — Neutral", "4", "5 — Strongly Agree"],
                        horizontal=True, key="pu2", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(_dots(2), unsafe_allow_html=True)

        # B3 — PU Decision Aid
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">Using this AI report would help me make better financial decisions.</div>
            <span class="scale-cite">Perceived Usefulness — Davis (1989) · Question 3 of 4</span>
        </div>""", unsafe_allow_html=True)
        pu3 = st.radio("Rate B3", ["1 — Strongly Disagree", "2", "3 — Neutral", "4", "5 — Strongly Agree"],
                        horizontal=True, key="pu3", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(_dots(3), unsafe_allow_html=True)

        # C — Behavioural Intent
        st.markdown("""
        <div class="scale-block">
            <div class="scale-q">After seeing this report, what is your most likely next step?</div>
            <span class="scale-cite">Behavioural Intent · Question 4 of 4 — almost done!</span>
        </div>""", unsafe_allow_html=True)
        intent = st.radio("Intent", [
            "Reduce discretionary spending",
            "Seek cheaper housing",
            "Look for additional income",
            "No change planned",
        ], key="intent_val", label_visibility="collapsed")

        st.markdown("---")
        st.markdown("""
        <div style="text-align:center;margin-bottom:12px">
            <div style="font-size:0.82rem;color:var(--text-muted)">
                🔒 Submitting saves your data permanently and reveals your final score
            </div>
        </div>""", unsafe_allow_html=True)
        lock = st.form_submit_button("🔓  Submit & Unlock My Full Result  →", use_container_width=True)

    if lock:
        # Parse Likert labels back to integers
        lmap = {"1 — Strongly Disagree": 1, "2": 2, "3 — Neutral": 3, "4": 4, "5 — Strongly Agree": 5}
        pu1_i, pu2_i, pu3_i = lmap.get(pu1, 3), lmap.get(pu2, 3), lmap.get(pu3, 3)
        pu_composite = round((pu1_i + pu2_i + pu3_i) / 3, 2)
        with st.spinner("Saving your results…"):
            sheet = connect_to_sheet()
            if sheet and st.session_state.get("target_row"):
                try:
                    r = st.session_state.target_row
                    sheet.update([[pu_composite, pu_composite]], f"H{r}:I{r}")
                    sheet.update_cell(r, 19, intent)
                    sheet.update([[pu1_i, pu2_i, pu3_i]], f"U{r}:W{r}")
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
