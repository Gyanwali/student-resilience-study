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
    "https://www.googleapis.com/auth/drive"
]

st.set_page_config(page_title="Resilience Lab AI", page_icon="🛡️", layout="centered")

# ──────────────────────────────────────────────
# STYLING
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: #0a0e1a; color: #e2e8f0; }
#MainMenu, footer, header { visibility: hidden; }

.top-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem; color: #38bdf8;
    letter-spacing: 0.2em; text-transform: uppercase;
    border: 1px solid #38bdf8; display: inline-block;
    padding: 4px 12px; border-radius: 2px; margin-bottom: 1rem;
}
.hero-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.6rem; font-weight: 600;
    color: #f1f5f9; line-height: 1.2; margin-bottom: 0.5rem;
}
.hero-sub {
    font-size: 1rem; color: #94a3b8;
    margin-bottom: 2rem; font-weight: 300;
}
.card {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 12px; padding: 24px; margin-bottom: 1rem;
}
.metric-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 12px; margin: 1.5rem 0;
}
.metric-card {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 10px; padding: 20px 16px;
    text-align: center; position: relative; overflow: hidden;
}
.metric-card::before {
    content: ''; position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem; font-weight: 600;
    color: #38bdf8; display: block;
}
.metric-label {
    font-size: 0.72rem; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px;
}
.analysis-box {
    background: linear-gradient(135deg, #0f172a, #111827);
    border: 1px solid #1e40af; border-left: 4px solid #38bdf8;
    border-radius: 10px; padding: 20px 24px;
    margin: 1.5rem 0; line-height: 1.8;
    color: #cbd5e1; font-size: 0.95rem;
}
.analysis-box b { color: #f1f5f9; }
.analysis-box .highlight {
    color: #38bdf8; font-family: 'IBM Plex Mono', monospace; font-weight: 600;
}
.pid-chip {
    font-family: 'IBM Plex Mono', monospace;
    background: #0f172a; border: 1px solid #334155;
    border-radius: 6px; padding: 6px 14px;
    font-size: 0.8rem; color: #38bdf8;
    display: inline-block; margin-bottom: 1.5rem;
}
.step-bar { display: flex; gap: 8px; margin-bottom: 2rem; }
.step { flex: 1; height: 4px; border-radius: 2px; background: #1e293b; }
.step.active { background: linear-gradient(90deg, #38bdf8, #818cf8); }
.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem; color: #475569;
    text-transform: uppercase; letter-spacing: 0.15em;
    margin: 1.5rem 0 0.75rem 0;
    border-bottom: 1px solid #1e293b; padding-bottom: 8px;
}
.success-id {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.4rem; color: #38bdf8;
    background: #0f172a; border: 1px solid #1e40af;
    border-radius: 8px; padding: 16px 24px;
    text-align: center; margin: 1.5rem 0; letter-spacing: 0.05em;
}

/* Insight cards for dashboard */
.insight-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 12px; margin: 1rem 0;
}
.insight-card {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 10px; padding: 16px 18px;
}
.insight-card .i-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem; color: #475569;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;
}
.insight-card .i-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem; font-weight: 600; color: #f1f5f9;
}
.insight-card .i-sub { font-size: 0.78rem; color: #64748b; margin-top: 4px; }

/* Score gauge color classes */
.score-low { color: #ef4444; }
.score-mid { color: #f59e0b; }
.score-high { color: #34d399; }

/* Formula box */
.formula-box {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 8px; padding: 14px 18px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem; color: #94a3b8;
    margin: 0.75rem 0; line-height: 1.9;
}
.formula-box span { color: #38bdf8; }

/* Benchmark bar */
.bench-row { margin: 10px 0; }
.bench-label { font-size: 0.8rem; color: #94a3b8; margin-bottom: 4px; }
.bench-track {
    background: #1e293b; border-radius: 4px;
    height: 10px; width: 100%; position: relative;
}
.bench-fill {
    height: 10px; border-radius: 4px;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
}
.bench-marker {
    position: absolute; top: -3px;
    width: 4px; height: 16px;
    background: #f59e0b; border-radius: 2px;
}

.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important; letter-spacing: 0.05em !important;
    height: 3rem !important; width: 100% !important; font-weight: 600 !important;
}
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important; height: 3rem !important;
    width: 100% !important; font-weight: 600 !important;
}
hr { border-color: #1e293b !important; margin: 1.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

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
    response = sheet.append_row(row_data, value_input_option="USER_ENTERED")
    updated_range = response["updates"]["updatedRange"]
    match = re.search(r':.*?(\d+)$', updated_range)
    return int(match.group(1)) if match else None

# ──────────────────────────────────────────────
# AI ENGINE
# ──────────────────────────────────────────────
def run_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    exp_vals = {
        "Housing": float(data['rent']) * 4.33,
        "Groceries": float(data['groc']) * 4.33,
        "Lifestyle": float(data['uber']) * 4.33,
        "Transport": float(data['trans']) * 4.33,
        "Bills": float(data['bills']),
        "Remittance": float(data['remit']),
    }
    m_exp = sum(exp_vals.values())
    surplus = m_inc - m_exp
    savings = float(data['savings'])
    runway = round(savings / m_exp, 1) if m_exp > 0 else 0.0

    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5
    prob = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus / 500)), 1)

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

    # Score component breakdown for explanation tab
    score_components = {
        "Surplus Ratio (×40)": round((surplus / m_inc) * 40, 1),
        "Financial Literacy (×0.2)": round(lit_map[data['lit']] * 0.2, 1),
        "Family Support (+20)": 20 if data['p_supp'] == "Yes" else 0,
        "Base Score (+30)": 30,
        "Meal-Skip Penalty (−25)": -25 if data['meals'] == "Yes" else 0,
    }

    return {
        "surplus": round(surplus, 2),
        "m_inc": round(m_inc, 2),
        "m_exp": round(m_exp, 2),
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob, 100.0),
        "runway": runway,
        "rent_pct": rent_pct,
        "uber_pct": uber_pct,
        "groc_pct": groc_pct,
        "trans_pct": trans_pct,
        "save_rate": save_rate,
        "exp_breakdown": exp_vals,
        "flags": flags,
        "score_components": score_components,
        "lit_score": lit_map[data['lit']],
    }

# ──────────────────────────────────────────────
# SESSION INIT
# ──────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = "home"

# ──────────────────────────────────────────────
# FINISHED
# ──────────────────────────────────────────────
if st.session_state.step == "finished":
    st.balloons()
    st.markdown('<div class="top-badge">Research Complete</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Data Secured ✓</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Your response has been recorded. Thank you for contributing.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="success-id">Participant ID: {st.session_state.get("last_id","—")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="analysis-box">You may safely close this window. Data is used solely for academic research on financial resilience among international students in Sydney.</div>', unsafe_allow_html=True)
    st.stop()

# ──────────────────────────────────────────────
# HOME
# ──────────────────────────────────────────────
if st.session_state.step == "home":
    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="top-badge">Sydney · Academic Research · 2025</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br>Lab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">The impact of predictive AI analytics on the financial resilience of international students — focusing on discretionary spending behaviour.</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <div class="section-header">What to expect</div>
        Takes approximately <b>3 minutes</b>. You will provide anonymised financial data and receive
        a personalised AI resilience report with charts and breakdowns. All data is encrypted and
        used for academic purposes only.
    </div>""", unsafe_allow_html=True)
    consent = st.checkbox("I voluntarily consent to participate in this research study and understand my data will be anonymised.")
    if consent:
        if st.button("▶  INITIALISE SESSION"):
            st.session_state.participant_id = f"RES-{random.randint(100000, 999999)}"
            st.session_state.step = "inputs"
            st.rerun()

# ──────────────────────────────────────────────
# INPUTS
# ──────────────────────────────────────────────
elif st.session_state.step == "inputs":
    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step active"></div><div class="step"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Financial<br>Profile</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">All figures are monthly unless stated otherwise.</div>', unsafe_allow_html=True)

    with st.form("input_form"):
        st.markdown('<div class="section-header">Location</div>', unsafe_allow_html=True)
        suburbs = sorted(["Hurstville","Parramatta","Sydney CBD","Randwick","Strathfield",
                           "Burwood","Auburn","Kensington","Rhodes","Wolli Creek","Other"])
        addr = st.selectbox("Suburb of Residence", suburbs)
        custom_sub = st.text_input("If 'Other', please specify:", placeholder="e.g. Chatswood")
        final_addr = custom_sub.strip() if addr == "Other" else addr

        st.markdown('<div class="section-header">Income</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            inc = st.number_input("Monthly Income (AUD $)", min_value=0, max_value=15000, value=3200, step=50)
        with col2:
            p_supp = st.radio("Receiving Family Support?", ["No","Yes"], horizontal=True)
        p_amt = st.number_input("Family Support Amount ($/mo) — enter 0 if none", min_value=0, max_value=5000, value=0, step=50)

        st.markdown('<div class="section-header">Core Weekly Expenses</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: rent  = st.number_input("Rent ($/wk)",       min_value=0, max_value=2000, value=450, step=10)
        with col2: groc  = st.number_input("Groceries ($/wk)",  min_value=0, max_value=500,  value=140, step=10)
        with col3: trans = st.number_input("Transport ($/wk)",  min_value=0, max_value=300,  value=45,  step=5)

        st.markdown('<div class="section-header">Discretionary Spending</div>', unsafe_allow_html=True)
        uber = st.slider("Uber / Eating Out / Lifestyle ($/wk)", min_value=0, max_value=800, value=120, step=10)

        st.markdown('<div class="section-header">Financial Position</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: bills   = st.number_input("Fixed Bills ($/mo)", min_value=0, max_value=1000,  value=150, step=10)
        with col2: remit   = st.number_input("Remittance ($/mo)",  min_value=0, max_value=3000,  value=0,   step=50)
        with col3: savings = st.number_input("Total Savings ($)",  min_value=0, max_value=100000,value=2000,step=100)

        st.markdown('<div class="section-header">Background</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: lit    = st.select_slider("Financial Literacy Level", options=["Novice","Intermediate","Advanced"], value="Intermediate")
        with col2: months = st.number_input("Months Living in Sydney", min_value=1, max_value=120, value=12)
        meals = st.radio("Have you skipped meals due to lack of money in the past month?", ["No","Yes"], horizontal=True)

        st.markdown("---")
        submitted = st.form_submit_button("⚡  GENERATE AI REPORT")

    if submitted:
        if addr == "Other" and not final_addr:
            st.warning("Please specify your suburb.")
        else:
            data = {"income":inc,"p_supp":p_supp,"p_amt":p_amt,"remit":remit,
                    "rent":rent,"uber":uber,"groc":groc,"trans":trans,"bills":bills,
                    "meals":meals,"addr":final_addr,"savings":savings,"lit":lit,"months":months}
            res = run_model(data)
            st.session_state.data = data
            st.session_state.res  = res
            with st.spinner("Saving to research database..."):
                sheet = connect_to_sheet()
                if sheet:
                    sydney_time = datetime.utcnow() + timedelta(hours=11)
                    row = [sydney_time.strftime("%Y-%m-%d %H:%M"),
                           st.session_state.participant_id,
                           rent, inc, final_addr, uber, "", "",
                           res['score'], meals, p_supp, remit,
                           p_amt, savings, trans, lit, months, ""]
                    try:
                        st.session_state.target_row = append_and_get_row(sheet, row)
                    except Exception as e:
                        st.error(f"❌ Failed to save: {e}"); st.stop()
                else:
                    st.stop()
            st.session_state.step = "results"
            st.rerun()

# ──────────────────────────────────────────────
# RESULTS
# ──────────────────────────────────────────────
elif st.session_state.step == "results":
    ai   = st.session_state.res
    data = st.session_state.data

    st.markdown('<div class="step-bar"><div class="step active"></div><div class="step active"></div><div class="step active"></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pid-chip">SESSION · {st.session_state.participant_id}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Resilience<br>Dashboard</div>', unsafe_allow_html=True)

    # ── Top metrics ──
    surplus_display = f"+${ai['surplus']}" if ai['surplus'] >= 0 else f"-${abs(ai['surplus'])}"
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <span class="metric-value">{ai['score']}</span>
            <div class="metric-label">Resilience Score</div>
        </div>
        <div class="metric-card">
            <span class="metric-value">{ai['runway']}</span>
            <div class="metric-label">Runway (months)</div>
        </div>
        <div class="metric-card">
            <span class="metric-value">{ai['prob']}%</span>
            <div class="metric-label">Stability Prob.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── AI narrative ──
    flags_html = "".join(f"<li style='margin:6px 0'>{f}</li>" for f in ai['flags']) if ai['flags'] else "<li>✅ No critical stress indicators detected.</li>"
    st.markdown(f"""
    <div class="analysis-box">
        <b>AI Analysis — {data['addr']}</b><br><br>
        Housing costs represent <span class="highlight">{ai['rent_pct']}%</span> of total income
        and discretionary spending accounts for <span class="highlight">{ai['uber_pct']}%</span>.
        Monthly surplus is <span class="highlight">{surplus_display}</span> with a financial runway
        of <span class="highlight">{ai['runway']} months</span>.<br><br>
        <b>Key Indicators:</b>
        <ul style="margin:8px 0 0 0; padding-left:18px">{flags_html}</ul>
    </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════
    # TABS
    # ════════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Spending Breakdown",
        "📈 Benchmarks",
        "🔬 Score Explained",
        "💡 Recommendations"
    ])

    CHART_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="IBM Plex Mono"),
        margin=dict(t=30, b=30, l=10, r=10),
    )
    COLORS = ["#38bdf8","#818cf8","#34d399","#fb923c","#f472b6","#a78bfa"]

    # ── TAB 1: Spending Breakdown ──────────────
    with tab1:
        st.markdown('<div class="section-header">Monthly Expense Distribution</div>', unsafe_allow_html=True)
        fig_pie = px.pie(
            values=list(ai['exp_breakdown'].values()),
            names=list(ai['exp_breakdown'].keys()),
            hole=0.55, color_discrete_sequence=COLORS
        )
        fig_pie.update_layout(**CHART_LAYOUT, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)))
        fig_pie.update_traces(textfont_color="#e2e8f0")
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown('<div class="section-header">Income vs Expenditure</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Total Income", "Total Expenses", "Monthly Surplus"],
            y=[ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)],
            marker_color=["#34d399", "#f472b6", "#38bdf8"],
            text=[f"${v:,.0f}" for v in [ai['m_inc'], ai['m_exp'], max(ai['surplus'], 0)]],
            textposition="outside", textfont=dict(color="#e2e8f0", size=12)
        ))
        fig_bar.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(showgrid=False, showticklabels=False),
            xaxis=dict(showgrid=False),
            showlegend=False, height=320
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown('<div class="section-header">Expense Share of Income (%)</div>', unsafe_allow_html=True)
        categories  = list(ai['exp_breakdown'].keys())
        monthly_exp = list(ai['exp_breakdown'].values())
        pct_vals    = [round(v / ai['m_inc'] * 100, 1) for v in monthly_exp]
        fig_h = go.Figure(go.Bar(
            x=pct_vals, y=categories, orientation='h',
            marker=dict(color=COLORS[:len(categories)]),
            text=[f"{p}%" for p in pct_vals],
            textposition="outside", textfont=dict(color="#e2e8f0")
        ))
        fig_h.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
            showlegend=False, height=300
        )
        st.plotly_chart(fig_h, use_container_width=True)

    # ── TAB 2: Benchmarks ──────────────────────
    with tab2:
        st.markdown('<div class="section-header">Your Spending vs Sydney Benchmarks</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="analysis-box" style="font-size:0.85rem">
        Benchmarks are based on the <b>50/30/20 rule</b> adapted for Sydney international students.
        The yellow marker (▐) shows your position; the bar shows the recommended safe zone.
        </div>""", unsafe_allow_html=True)

        benchmarks = [
            ("Housing % of Income",     ai['rent_pct'],  30, 40,  "%"),
            ("Discretionary % of Income",ai['uber_pct'], 10, 20,  "%"),
            ("Groceries % of Income",   ai['groc_pct'],  10, 18,  "%"),
            ("Transport % of Income",   ai['trans_pct'],  5, 12,  "%"),
            ("Savings Rate",            ai['save_rate'],  20, 30, "%"),
        ]

        for label, val, rec_lo, rec_hi, unit in benchmarks:
            color = "#34d399" if rec_lo <= val <= rec_hi else ("#f59e0b" if val < rec_lo else "#ef4444")
            st.markdown(f"""
            <div class="bench-row">
                <div class="bench-label">{label} &nbsp;
                    <span style="font-family:'IBM Plex Mono';color:{color};font-weight:600">{val}{unit}</span>
                    <span style="font-size:0.72rem;color:#475569"> · recommended {rec_lo}–{rec_hi}{unit}</span>
                </div>
                <div class="bench-track">
                    <div class="bench-fill" style="width:{min(val/50*100,100):.0f}%;background:{color}80"></div>
                    <div class="bench-marker" style="left:{min(val/50*100,100):.0f}%"></div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Spending Radar</div>', unsafe_allow_html=True)
        radar_cats   = ["Housing","Groceries","Lifestyle","Transport","Bills","Remittance"]
        radar_vals   = [ai['rent_pct'], ai['groc_pct'], ai['uber_pct'], ai['trans_pct'],
                        round(float(data['bills']) / ai['m_inc'] * 100, 1),
                        round(float(data['remit']) / ai['m_inc'] * 100, 1)]
        bench_vals   = [30, 14, 15, 8, 5, 5]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=bench_vals + [bench_vals[0]], theta=radar_cats + [radar_cats[0]],
            fill='toself', name='Benchmark',
            line=dict(color='#34d399', dash='dash'), fillcolor='rgba(52,211,153,0.08)'))
        fig_radar.add_trace(go.Scatterpolar(r=radar_vals + [radar_vals[0]], theta=radar_cats + [radar_cats[0]],
            fill='toself', name='Your Profile',
            line=dict(color='#38bdf8'), fillcolor='rgba(56,189,248,0.15)'))
        fig_radar.update_layout(
            **CHART_LAYOUT,
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0, 50], color='#475569', gridcolor='#1e293b'),
                angularaxis=dict(color='#94a3b8', gridcolor='#1e293b')
            ),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
            height=380
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── TAB 3: Score Explained ─────────────────
    with tab3:
        st.markdown('<div class="section-header">How Your Score Was Calculated</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="formula-box">
            Score = <span>(Surplus / Income) × 40</span><br>
                  + <span>Financial Literacy × 0.2</span><br>
                  + <span>Family Support Bonus (20 if Yes)</span><br>
                  + <span>Base Score (30)</span><br>
                  − <span>Meal-Skip Penalty (25 if Yes)</span><br>
            → Clamped between <span>5</span> and <span>100</span>
        </div>""", unsafe_allow_html=True)

        # Waterfall chart of score components
        components = ai['score_components']
        labels = list(components.keys()) + ["Final Score"]
        values = list(components.values())
        running = 0
        measures = []
        for v in values:
            measures.append("relative")
            running += v
        measures.append("total")
        values_wf = values + [None]

        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=values + [running],
            connector=dict(line=dict(color="#1e293b", width=1)),
            increasing=dict(marker_color="#34d399"),
            decreasing=dict(marker_color="#ef4444"),
            totals=dict(marker_color="#38bdf8"),
            text=[f"{v:+.1f}" if v else f"{running:.0f}" for v in values + [running]],
            textposition="outside",
            textfont=dict(color="#e2e8f0")
        ))
        fig_wf.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(showgrid=False, range=[min(0, min(values))-10, max(running, 100)+15]),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            showlegend=False, height=380
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        score_color = "#34d399" if ai['score'] >= 60 else ("#f59e0b" if ai['score'] >= 35 else "#ef4444")
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
                <div class="i-value">{ai['lit_score']}</div>
                <div class="i-sub">Level: {data['lit']}</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Monthly Surplus</div>
                <div class="i-value" style="color:{'#34d399' if ai['surplus']>=0 else '#ef4444'}">{surplus_display}</div>
                <div class="i-sub">Income − All Expenses</div>
            </div>
            <div class="insight-card">
                <div class="i-label">Stability Probability</div>
                <div class="i-value">{ai['prob']}%</div>
                <div class="i-sub">Logistic model on surplus ratio</div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── TAB 4: Recommendations ─────────────────
    with tab4:
        st.markdown('<div class="section-header">AI-Generated Recommendations</div>', unsafe_allow_html=True)

        recs = []

        if ai['rent_pct'] > 40:
            recs.append(("🏠 Housing", f"Your rent is {ai['rent_pct']}% of income. Consider shared accommodation in suburbs like Auburn, Hurstville, or Parramatta where average rents are 15–25% lower than the CBD."))
        if ai['uber_pct'] > 15:
            monthly_uber = round(float(data['uber']) * 4.33, 0)
            saving = round(monthly_uber * 0.4, 0)
            recs.append(("🍔 Discretionary Spend", f"Reducing Uber/lifestyle spend by 40% could free up ~${saving}/mo. Cook at home 4–5 days/week and use Opal card for transport instead of rideshare."))
        if ai['runway'] < 3:
            recs.append(("💰 Emergency Fund", f"With only {ai['runway']} months of runway, aim to build a buffer of at least 3 months. Even saving $50–100/week accelerates this significantly."))
        if float(data['remit']) > ai['m_inc'] * 0.15:
            recs.append(("💸 Remittance", "Remittances exceed 15% of income. Explore lower-fee transfer services (Wise, Remitly) and consider batching transfers monthly to reduce fees."))
        if data['lit'] == "Novice":
            recs.append(("📚 Financial Literacy", "Improving financial knowledge can significantly boost resilience. Free resources: MoneySmart (ASIC), Student Edge, and your university's financial counselling service."))
        if data['meals'] == "Yes":
            recs.append(("🍱 Food Security", "Meal-skipping is a critical stress indicator. Access free or subsidised meals at your university's student hub, or register with OzHarvest and Foodbank NSW."))
        if ai['surplus'] < 0:
            recs.append(("⚡ Urgent: Deficit", f"You are spending ${abs(ai['surplus'])}/mo more than you earn. Contact your university's financial hardship office immediately for emergency assistance options."))

        if not recs:
            recs.append(("✅ Looking Good", "Your financial profile shows no critical stress points. Continue maintaining your surplus and consider increasing your savings rate toward 20%."))

        for icon_title, body in recs:
            st.markdown(f"""
            <div class="card" style="margin-bottom:12px">
                <div style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem;
                            color:#38bdf8;margin-bottom:8px">{icon_title}</div>
                <div style="font-size:0.9rem;color:#cbd5e1;line-height:1.7">{body}</div>
            </div>""", unsafe_allow_html=True)

        # Savings projection chart
        st.markdown('<div class="section-header">Savings Projection (12 months)</div>', unsafe_allow_html=True)
        months_proj = list(range(0, 13))
        current_sav = float(data['savings'])
        monthly_add = max(ai['surplus'], 0)
        proj_base   = [current_sav + monthly_add * m for m in months_proj]
        proj_opt    = [current_sav + (monthly_add * 1.2) * m for m in months_proj]

        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=months_proj, y=proj_base, name="Current trajectory",
            line=dict(color="#38bdf8", width=2),
            fill='tozeroy', fillcolor='rgba(56,189,248,0.07)'
        ))
        fig_proj.add_trace(go.Scatter(
            x=months_proj, y=proj_opt, name="If 20% more saved",
            line=dict(color="#34d399", width=2, dash='dash')
        ))
        fig_proj.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(title="Months", showgrid=False, color="#475569"),
            yaxis=dict(title="Savings ($)", showgrid=False, color="#475569"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
            height=300
        )
        st.plotly_chart(fig_proj, use_container_width=True)

    # ════════════════════════════════════════════
    # FEEDBACK FORM  (always visible below tabs)
    # ════════════════════════════════════════════
    st.markdown("---")
    st.markdown('<div class="section-header">Research Evaluation</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="font-size:0.9rem">Please evaluate the AI report before submitting your final response.</div>', unsafe_allow_html=True)

    with st.form("feedback_form"):
        col1, col2 = st.columns(2)
        with col1:
            trust  = st.select_slider("How much do you trust the AI analysis?", options=["Low","Neutral","High"], value="Neutral")
        with col2:
            useful = st.select_slider("Was this report enlightening?", options=["No","Neutral","Yes"], value="Neutral")
        intent = st.radio(
            "After seeing this report, what is your most likely next action?",
            ["Reduce discretionary spending","Search for cheaper housing","Seek additional income","No change planned"]
        )
        st.markdown("---")
        lock = st.form_submit_button("🔒  SUBMIT & LOCK RESPONSE")

    if lock:
        with st.spinner("Locking your response..."):
            sheet = connect_to_sheet()
            if sheet and st.session_state.get("target_row"):
                try:
                    row_idx = st.session_state.target_row
                    sheet.update([[trust, useful]], f"G{row_idx}:H{row_idx}")
                    sheet.update_cell(row_idx, 18, intent)
                    st.session_state.last_id = st.session_state.participant_id
                    st.session_state.step = "finished"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save feedback: {e}")
            elif not st.session_state.get("target_row"):
                st.error("⚠️ Row reference lost — please restart the survey.")
            else:
                st.error("❌ Could not connect to sheet.")
