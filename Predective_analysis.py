import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. RESEARCH DATA CORE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"


def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_info)
        return client.open_by_url(SHEET_URL).sheet1
    except:
        return None


# --- 2. ELITE FINTECH UI (High-Contrast & Projector Optimized) ---
st.set_page_config(page_title="Resilience Lab AI", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #F8FAFC !important; font-family: 'Inter', sans-serif; }

    /* UNIVERSAL TEXT VISIBILITY FIX */
    p, span, div, label, .stMarkdown p, h1, h2, h3, h4, .stMetric label { 
        color: #73705E !important; 
        font-weight: 700 !important; 
    }

    /* Metric Styling */
    [data-testid="stMetricValue"] { color: #2563EB !important; font-weight: 800 !important; font-size: 2.2rem !important; }

    /* Dark Mode Navigation Header */
    .nav-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 45px; text-align: center; border-radius: 0 0 30px 30px; margin-bottom: 40px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
    }
    .nav-header h1 { color: #FFFFFF !important; font-size: 2.8rem; margin: 0; letter-spacing: -1px; }
    .nav-header p { color: #38BDF8 !important; font-weight: 600 !important; font-size: 1.1rem; margin-top: 10px; }

    /* Input Styling */
    div[data-baseweb="input"] { background-color: #E0F2FE !important; border: 2px solid #0F172A !important; border-radius: 12px !important; }
    div[data-testid="stTextInput"]:has(label:contains("Suburb Address")) div[data-baseweb="input"] { background-color: #FFFFFF !important; }

    /* LANDING PAGE MEGA BUTTON */
    .mega-btn-container { display: flex; justify-content: center; padding: 60px 0; }
    .mega-btn-container div[data-testid="stButton"] button {
        background-color: #2563EB !important; color: white !important;
        height: 5.5rem !important; width: 650px !important; border-radius: 20px; 
        font-weight: 800; border: none; font-size: 1.7rem;
        box-shadow: 0 25px 50px -12px rgba(37, 99, 235, 0.4);
        text-transform: uppercase; transition: 0.3s;
    }
    .mega-btn-container div[data-testid="stButton"] button:hover { transform: scale(1.02); background-color: #1D4ED8 !important; }
    .mega-btn-container div[data-testid="stButton"] button p { color: white !important; }

    /* Dashboard Cards */
    .res-card {
        background: white; padding: 40px; border-radius: 25px;
        border: 1px solid #E2E8F0; margin-bottom: 30px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Shock Simulation Box */
    .shock-box {
        background: #FFF1F2; border: 3px solid #FB7185;
        padding: 25px; border-radius: 15px; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. STATE & NAVIGATION ---
if 'step' not in st.session_state: st.session_state.step = "home"
if 'data' not in st.session_state: st.session_state.data = {}


def nav(target):
    st.session_state.step = target
    st.rerun()


# --- 4. PREDICTIVE LOGIC ENGINE ---
def run_research_model(data):
    m_inc = max(data['income'] + data['p_amt'], 1)
    m_exp = (data['rent'] + data['groc'] + data['uber'] + data['trans']) * 4.33 + data['bills'] + data['remit']
    surplus = m_inc - m_exp
    runway = round(max(data['savings'], 0) / (m_exp if m_exp > 0 else 1), 1)

    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25

    # Stress Simulation (10% Rent Hike)
    shock_rent = (data['rent'] * 1.10) * 4.33
    shock_surplus = m_inc - (
                shock_rent + (data['groc'] + data['uber'] + data['trans']) * 4.33 + data['bills'] + data['remit'])

    return {
        "m_surplus": round(surplus, 2), "score": int(min(max(score, 5), 100)),
        "status": "RESILIENT" if score > 55 else "VULNERABLE",
        "runway": runway, "uber_pct": round(((data['uber'] * 4.33) / m_inc) * 100, 1),
        "rent_pct": round(((data['rent'] * 4.33) / m_inc) * 100, 1),
        "shock_surplus": round(shock_surplus, 2),
        "chart_vals": [data['rent'] * 4.33, data['groc'] * 4.33, data['uber'] * 4.33, data['remit'],
                       data['trans'] * 4.33 + data['bills']],
        "chart_labs": ["Rent", "Groceries", "UberEats/Dining", "Family Remit", "Utils/Transport"]
    }


# --- 5. PAGE ROUTING ---
st.markdown(
    '<div class="nav-header"><h1>Resilience Intelligence Lab</h1><p>Master\'s Research Terminal | Excelsia College</p></div>',
    unsafe_allow_html=True)

if st.session_state.step == "home":
    st.markdown("""<div class="res-card" style="text-align:center;">
        <h2 style="font-size:2.6rem; margin-bottom:20px;">Predictive Behavioral Diagnostics</h2>
        <p style="font-size:1.4rem; max-width:900px; margin: 0 auto; line-height:1.7;">
        Exploring the impact of <b>Explainable AI (XAI)</b> on the financial shock-absorption of international students. 
        This terminal simulates behavioral pivots to calculate real-world resilience metrics.</p>
        <hr style="margin:40px 0; opacity:0.1;">
        <p style="font-size:1.1rem; color:#64748B;">Researcher: <b>Sandeep Sharma</b> | contact: sandeepgyanwalli@gmail.com</p>
    </div>""", unsafe_allow_html=True)
    st.markdown('<div class="mega-btn-container">', unsafe_allow_html=True)
    if st.button("INITIALIZE AI DIAGNOSTIC"): nav("inputs")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.step == "inputs":
    with st.container():
        st.markdown('<div class="res-card"><h3>📍 Contextual Background</h3>', unsafe_allow_html=True)
        c_sub, c_ten = st.columns([2, 1])
        with c_sub:
            addr = st.text_input("Suburb Address", placeholder="e.g. Hurstville, NSW")
        with c_ten:
            months = st.number_input("Months in Sydney", min_value=0, value=12)
        lit = st.select_slider("Financial Literacy Level", options=["Novice", "Intermediate", "Advanced"],
                               value="Intermediate")

        st.markdown('<h3>💰 Liquidity & Cashflow</h3>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            inc = st.number_input("Monthly Job Salary (AUD)", value=3000)
        with col2:
            p_supp = st.radio("Access to Family Support?", ["No", "Yes"])
        with col3:
            p_amt = st.number_input("Monthly Support Amount", value=0) if p_supp == "Yes" else 0

        col4, col5 = st.columns(2)
        with col4:
            savings = st.number_input("Current Savings (AUD)", value=2500)
        with col5:
            remit = st.number_input("Monthly Remittance (Sent Home)", value=0)

        st.markdown('<h3>📉 Behavioral Spending (Weekly)</h3>', unsafe_allow_html=True)
        col6, col7, col8 = st.columns(3)
        with col6:
            rent = st.number_input("Weekly Rent", value=450)
        with col7:
            uber = st.number_input("Weekly UberEats/Dining", value=120)
        with col8:
            groc = st.number_input("Weekly Groceries", value=130)
        col9, col10 = st.columns(2)
        with col9:
            trans = st.number_input("Weekly Transport", value=45)
        with col10:
            bills = st.number_input("Monthly Utilities", value=150)

        meals = st.radio("Skipped meals recently to save money?", ["No", "Yes"])
        consent = st.checkbox("I consent to participate in this academic research study.")
        if st.button("RUN PREDICTIVE IMPACT ANALYSIS"):
            if consent and addr:
                st.session_state.data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent,
                                         "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals,
                                         "addr": addr, "savings": savings, "lit": lit, "months": months}
                nav("results")
            elif not addr:
                st.error("Please enter a suburb.")

elif st.session_state.step == "results":
    res = st.session_state.data
    ai = run_research_model(res)

    # DASHBOARD METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Resilience Index", f"{ai['score']}/100")
    m2.metric("Monthly Surplus", f"${ai['m_surplus']}")
    m3.metric("Financial Runway", f"{ai['runway']} Mo")
    m4.metric("UberEats Ratio", f"{ai['uber_pct']}%")

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="res-card"><h4>Financial Distribution</h4>', unsafe_allow_html=True)
        fig_p = px.pie(values=ai['chart_vals'], names=ai['chart_labs'], hole=0.5,
                       color_discrete_sequence=px.colors.qualitative.Plotly)
        fig_p.update_layout(showlegend=False, height=300, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_p, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="res-card"><h4>Resilience Prediction Index</h4>', unsafe_allow_html=True)
        fig_g = go.Figure(go.Indicator(mode="gauge+number", value=ai['score'], gauge={'bar': {'color': "#2563EB"},
                                                                                      'steps': [{'range': [0, 40],
                                                                                                 'color': "#FEE2E2"},
                                                                                                {'range': [40, 75],
                                                                                                 'color': "#FEF3C7"},
                                                                                                {'range': [75, 100],
                                                                                                 'color': "#D1FAE5"}]}))
        fig_g.update_layout(height=300, margin=dict(t=30, b=0))
        st.plotly_chart(fig_g, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ⚡ SHOCK SIMULATION & REASONING
    st.markdown('<div class="res-card">', unsafe_allow_html=True)
    st.markdown("### ⚡ AI Stress Test Simulation (Market Shock 2026)")
    if ai['shock_surplus'] > 0:
        st.markdown(f"""<div class="shock-box" style="background: #ECFDF5; border-color: #10B981;">
        <h4 style="color: #065F46 !important;">Scenario: 10% Rental Hike</h4>
        <p>Your surplus remains positive at <b>${ai['shock_surplus']}</b>. Your behavioral profile is currently resilient to moderate market volatility.</p></div>""",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="shock-box">
        <h4 style="color: #BE123C !important;">Scenario: 10% Rental Hike</h4>
        <p>A 10% rent hike creates a monthly deficit of <b>${ai['shock_surplus']}</b>. This identifies a critical structural vulnerability.</p></div>""",
                    unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🤖 Explainable AI Behavioral Reasoning")
    st.write(f"• **Housing Load:** Rent is **{ai['rent_pct']}%** of income. (Rental Stress Threshold: 35%)")
    st.write(f"• **Behavioral Leak:** UberEats/Dining accounts for **{ai['uber_pct']}%** of your budget.")
    st.write(
        f"• **Safety Net Status:** {'Family support detected (Stabilizing factor)' if res['p_supp'] == 'Yes' else 'No family buffer detected (Self-reliant)'}.")

    st.markdown("#### 🗣️ Overall Behavioral Suggestion")
    st.write(
        f"The AI suggests that your **{res['lit']}** literacy level can be optimized by reducing discretionary UberEats spending by 25%. This shift creates the necessary annual buffer to survive the 10% rent hike simulated above.")
    st.markdown('</div>', unsafe_allow_html=True)

    if 'done' not in st.session_state:
        with st.form("sync"):
            st.markdown("### 📝 Research Feedback")
            trust = st.select_slider("Trust in AI Prediction (1-5)", options=[1, 2, 3, 4, 5], value=3)
            useful = st.radio("Did this intervention change your financial outlook?", ["Yes", "No", "Maybe"])
            if st.form_submit_button("SYNC DATA TO RESEARCH DATABASE"):
                sheet = connect_to_sheet()
                if sheet:
                    # COMPLETE 17-VARIABLE DATA SYNC
                    sheet.append_row(
                        [datetime.now().strftime("%Y-%m-%d"), "Yes", res['rent'], res['income'], res['addr'],
                         res['uber'], trust, useful, ai['score'], res['meals'], res['p_supp'], res['remit'],
                         res['p_amt'], res['savings'], res['trans'], res['lit'], res['months']])
                    st.session_state.done = True
                    st.balloons()
                    st.rerun()
    else:
        st.success("Research Data Successfully Synchronized.")
        if st.button("RESET SESSION"):
            del st.session_state.done
            nav("home")

st.markdown(
    '<div style="text-align:center; padding:30px; color:#94A3B8; font-weight:400;">Researcher: Sandeep Sharma | contact: sandeepgyanwalli@gmail.com</div>',
    unsafe_allow_html=True)