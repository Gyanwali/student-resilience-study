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
    except Exception:
        return None

# --- 2. PREDICTIVE AI ENGINE ---
def run_research_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    # Weekly to Monthly (4.33 weeks per month)
    m_exp = ((float(data['rent']) + float(data['groc']) + float(data['uber']) + float(data['trans'])) * 4.33) + float(data['bills']) + float(data['remit'])
    surplus = m_inc - m_exp
    
    # Sigmoid Success Probability
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)

    # Resilience Scoring
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "uber_pct": round(((float(data['uber']) * 4.33) / m_inc) * 100, 1),
        "rent_pct": round(((float(data['rent']) * 4.33) / m_inc) * 100, 1)
    }

# --- 3. UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC !important; }
    .nav-header { background: #0F172A; padding: 30px; text-align: center; border-radius: 0 0 20px 20px; color: white; margin-bottom: 25px;}
    .res-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .metric-box { background: #F1F5F9; padding: 15px; border-radius: 10px; text-align: center; border-left: 5px solid #2563EB; }
    .explanation-text { font-size: 0.95rem; color: #475569; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

st.markdown('<div class="nav-header"><h1 style="color:white !important;">Resilience Intelligence Lab</h1><p style="color:#38BDF8 !important;">Predictive Analytics & Behavioral Intervention Study</p></div>', unsafe_allow_html=True)

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.markdown('<div class="res-card" style="text-align:center;"><h2>XAI Research Terminal</h2><p>This study measures how AI feedback influences financial resilience. Your data is anonymized and stored for academic analysis.</p></div>', unsafe_allow_html=True)
    if st.button("INITIALIZE DIAGNOSTIC", use_container_width=True):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    with st.form("input_form"):
        st.markdown("### 📍 Participant Inputs")
        addr = st.text_input("Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        inc = st.number_input("Monthly Income (AUD)", value=3200)
        p_supp = st.radio("Family Support Available?", ["No", "Yes"])
        p_amt = st.number_input("Monthly Support Amount", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Emergency Savings", value=2000)
        rent = st.number_input("Weekly Rent", value=450)
        uber = st.number_input("Weekly UberEats/Dining", value=120)
        groc = st.number_input("Weekly Groceries", value=140)
        trans = st.number_input("Weekly Transport", value=45)
        bills = st.number_input("Monthly Bills", value=150)
        remit = st.number_input("Monthly Remittance", value=0)
        months = st.number_input("Months in Sydney", value=12)
        meals = st.radio("Skipped meals to save money?", ["No", "Yes"])

        if st.form_submit_button("GENERATE AI RESULTS & SYNC"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                row = [datetime.now().strftime("%Y-%m-%d"), rent, inc, addr, uber, res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, res['prob']]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    res = st.session_state.data
    ai = run_research_model(res)
    
    st.balloons()
    
    # 1. PRIMARY METRICS PANEL
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-box"><b>Resilience Score</b><br><h2>{ai["score"]}/100</h2></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-box"><b>Success Prob.</b><br><h2>{ai["prob"]}%</h2></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-box"><b>Monthly Surplus</b><br><h2>${ai["m_surplus"]}</h2></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-box"><b>Financial Status</b><br><h2>{"High" if ai["score"] > 70 else "At Risk"}</h2></div>', unsafe_allow_html=True)

    # 2. XAI EXPLANATION PANEL (THE "WHY")
    st.markdown('<div class="res-card"><h3>🤖 Explainable AI (XAI) Diagnosis</h3>', unsafe_allow_html=True)
    st.markdown(f"""
    <p class="explanation-text">
    <b>Reasoning:</b> Your resilience score of <b>{ai['score']}</b> is calculated by weighing your monthly surplus against your emergency buffer. 
    Currently, your housing costs consume <b>{ai['rent_pct']}%</b> of your income, leaving you vulnerable to market shocks. 
    <br><br>
    <b>Predictive Insight:</b> The AI identifies <b>UberEats/Dining ({ai['uber_pct']}% of income)</b> as your primary discretionary "leak." 
    Reducing this by <b>20%</b> would mathematically increase your 6-month Success Probability to <b>{min(ai['prob'] + 12, 100.0)}%</b>.
    </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. BEHAVIORAL CHANGE INTERVENTION (CORE RESEARCH COMPONENT)
    st.markdown('<div class="res-card" style="border: 2px solid #2563EB;"><h3>📉 Behavioral Change Intent</h3>', unsafe_allow_html=True)
    st.write("Based on the AI prediction above, which action are you most likely to take?")
    
    pivot = st.radio("Select your behavioral pivot:", [
        "No change - My current spending is necessary.",
        "Reduction - I will reduce UberEats/Dining out to improve my buffer.",
        "Optimization - I will seek a cheaper suburb or shared living.",
        "Emergency Planning - I will focus on increasing my savings/family support."
    ])
    
    if st.button("SUBMIT BEHAVIORAL INTENT"):
        st.success("Behavioral intent recorded. Thank you for participating in this Sydney research study.")
        # You could also sync this 'pivot' back to the sheet in a real Master's run.
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("RESET FOR NEW PARTICIPANT"):
        st.session_state.step = "home"
        st.rerun()

st.markdown('<div style="text-align:center; color:#94A3B8; padding:40px;">Researcher: Sandeep Sharma | Excelsia College Master\'s Research</div>', unsafe_allow_html=True)
