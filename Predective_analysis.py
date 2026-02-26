import streamlit as st
import gspread
import math
from datetime import datetime

# --- 1. RESEARCH INFRASTRUCTURE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"

def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_info)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception as e:
        return f"Error: {str(e)}"

# --- 2. PREDICTIVE AI ENGINE ---
def run_research_model(data):
    # Monthly Income Calculation
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    
    # Weekly to Monthly (4.33 weeks per month)
    weekly_items = float(data['rent']) + float(data['groc']) + float(data['uber']) + float(data['trans'])
    m_exp = (weekly_items * 4.33) + float(data['bills']) + float(data['remit'])
    
    surplus = m_inc - m_exp
    
    # Probability of Success (Logistic Sigmoid)
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)

    # Resilience Score Logic
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "uber_pct": round(((float(data['uber']) * 4.33) / m_inc) * 100, 1),
        "runway": round(max(float(data['savings']), 0) / (m_exp if m_exp > 0 else 1), 1)
    }

# --- 3. UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC !important; }
    [data-testid="stMetricValue"] { color: #2563EB !important; font-weight: 800; }
    .nav-header { background: #0F172A; padding: 30px; text-align: center; border-radius: 0 0 20px 20px; color: white; margin-bottom: 25px;}
    .res-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'step' not in st.session_state: st.session_state.step = "home"
if 'data' not in st.session_state: st.session_state.data = None

st.markdown('<div class="nav-header"><h1 style="color:white !important;">Resilience Intelligence Lab</h1><p style="color:#38BDF8 !important;">XAI Predictive Analytics | Sydney Student Study</p></div>', unsafe_allow_html=True)

# --- 4. APP NAVIGATION ---

# HOME PAGE
if st.session_state.step == "home":
    st.markdown('<div class="res-card" style="text-align:center;"><h2>Predictive Behavioral Diagnostics</h2><p>This terminal analyzes discretionary spending to predict financial shock-absorption.</p><hr><p><b>Lead Researcher:</b> Sandeep Sharma</p></div>', unsafe_allow_html=True)
    if st.button("INITIALIZE RESEARCH TERMINAL", use_container_width=True):
        st.session_state.step = "inputs"
        st.rerun()

# INPUT PAGE
elif st.session_state.step == "inputs":
    with st.form("research_input_form"):
        st.markdown('<div class="res-card"><h3>📍 Research Inputs</h3>', unsafe_allow_html=True)
        addr = st.text_input("Sydney Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        
        c1, c2 = st.columns(2)
        with c1: inc = st.number_input("Monthly Job Income (AUD)", value=3200)
        with c2: p_supp = st.radio("Family Support Available?", ["No", "Yes"])
        
        p_amt = st.number_input("Monthly Support Amount", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Total Emergency Savings", value=2000)
        rent = st.number_input("Weekly Rent", value=450)
        uber = st.number_input("Weekly UberEats/Dining", value=120)
        groc = st.number_input("Weekly Groceries", value=140)
        trans = st.number_input("Weekly Transport", value=45)
        bills = st.number_input("Monthly Utilities", value=150)
        remit = st.number_input("Monthly Remittance", value=0)
        months = st.number_input("Months in Sydney", value=12)
        meals = st.radio("Skipped meals to save money?", ["No", "Yes"])
        
        submit = st.form_submit_button("GENERATE AI PREDICTION & SYNC", use_container_width=True)
        
        if submit:
            data_payload = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data_payload
            
            # Connection and Sync
            sheet = connect_to_sheet()
            if hasattr(sheet, 'append_row'):
                res_calc = run_research_model(data_payload)
                row = [datetime.now().strftime("%Y-%m-%d"), rent, inc, addr, uber, res_calc['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, res_calc['prob']]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.step = "results"
                st.rerun()
            else:
                st.error(f"Sync failed: {sheet}")
    st.markdown('</div>', unsafe_allow_html=True)

# RESULTS PAGE
elif st.session_state.step == "results" and st.session_state.data:
    ai = run_research_model(st.session_state.data)
    
    st.balloons()
    st.markdown('<div class="res-card"><h3>📊 Resilience Intelligence Dashboard</h3>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Resilience Index", f"{ai['score']}/100")
    m2.metric("Success Prob.", f"{ai['prob']}%")
    m3.metric("Monthly Surplus", f"${ai['m_surplus']}")
    m4.metric("Runway", f"{ai['runway']} Mo")
    
    st.markdown("#### 🤖 XAI Reasoning")
    st.write(f"• **Critical Drain:** UberEats accounts for **{ai['uber_pct']}%** of your monthly income.")
    st.write(f"• **Status:** Your behavioral profile is classified as **{'Resilient' if ai['score'] > 60 else 'Vulnerable'}**.")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("RESET FOR NEW PARTICIPANT"):
        st.session_state.step = "home"
        st.session_state.data = None
        st.rerun()

st.markdown('<div style="text-align:center; color:#94A3B8; padding:40px;">Researcher: Sandeep Sharma | Excelsia College</div>', unsafe_allow_html=True)
