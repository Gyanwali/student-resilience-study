import streamlit as st
import gspread
import math
from datetime import datetime

# --- 1. SECURE RESEARCH INFRASTRUCTURE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"

def connect_to_sheet():
    try:
        # Pulling the credentials securely from Streamlit Cloud Secrets
        creds_info = dict(st.secrets["gcp_service_account"])
        
        # This line ensures the Private Key is formatted correctly for the Google API
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
        client = gspread.service_account_from_dict(creds_info)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception as e:
        return None

# --- 2. PREDICTIVE AI ENGINE (XAI LOGIC) ---
def run_research_model(data):
    # Total Monthly Income
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    
    # Weekly to Monthly conversion (4.33 weeks/month)
    m_exp = ((float(data['rent']) + float(data['groc']) + float(data['uber']) + float(data['trans'])) * 4.33) + float(data['bills']) + float(data['remit'])
    
    surplus = m_inc - m_exp
    
    # Sigmoid Logic for Success Probability (Academic Standard)
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)

    # Resilience Indexing Logic
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

# --- 3. MOBILE-OPTIMIZED UI ---
st.set_page_config(page_title="Resilience Lab", layout="centered") 
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .stButton button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        background-color: #2563EB !important; color: white !important; font-weight: bold; 
    }
    .res-card { 
        background: white; padding: 20px; border-radius: 15px; 
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 20px; 
    }
    .metric-box { background: #F1F5F9; padding: 15px; border-radius: 12px; text-align: center; border-left: 5px solid #2563EB; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "home":
    st.title("Resilience Lab AI")
    st.markdown('<div class="res-card"><h3>Participant Briefing</h3><p>This study explores predictive analytics in student finance. All data is anonymized and securely handled for Excelsia College research.</p></div>', unsafe_allow_html=True)
    if st.button("INITIALIZE RESEARCH TERMINAL"):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    with st.expander("📍 Suburb & Literacy", expanded=True):
        addr = st.text_input("Current Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
    
    with st.expander("💰 Income & Buffers", expanded=True):
        inc = st.number_input("Monthly Income (AUD)", value=3200)
        p_supp = st.radio("Access to family support?", ["No", "Yes"])
        p_amt = st.number_input("Monthly Support Amount", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Total Emergency Savings", value=2000)

    with st.expander("📉 Weekly Spending behavior", expanded=True):
        rent = st.number_input("Weekly Rent", value=450)
        uber = st.number_input("Weekly UberEats/Dining", value=120)
        groc = st.number_input("Weekly Groceries", value=140)
        trans = st.number_input("Weekly Transport", value=45)
        bills = st.number_input("Monthly Bills", value=150)
        remit = st.number_input("Monthly Remittance", value=0)
        months = st.number_input("Months in Sydney", value=12)
        meals = st.radio("Skipped meals to save money?", ["No", "Yes"])

    if st.button("GENERATE AI PREDICTION & SYNC"):
        data_pkg = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
        st.session_state.data = data_pkg
        
        with st.status("Securely syncing to Form Responses 1...", expanded=True) as status:
            sheet = connect_to_sheet()
            if sheet:
                res_v = run_research_model(data_pkg)
                # 15-Column Data Ingestion
                row = [datetime.now().strftime("%Y-%m-%d"), rent, inc, addr, uber, res_v['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, res_v['prob']]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                status.update(label="Sync Complete ✅", state="complete")
                st.session_state.step = "results"
                st.rerun()
            else:
                st.error("Connection Failed. Ensure your secrets are correctly pasted in Streamlit Cloud.")

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.markdown('<div class="res-card"><h3>📊 Resilience Intelligence Dashboard</h3>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="metric-box">Score<br><b>{ai["score"]}/100</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box">Success Prob.<br><b>{ai["prob"]}%</b></div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <p style='margin-top:20px;'><b>XAI Reasoning:</b> Your rent is <b>{ai['rent_pct']}%</b> of your income. 
    UberEats accounts for <b>{ai['uber_pct']}%</b> of your budget. 
    Reducing discretionary spending improves your success probability to <b>{min(ai['prob']+10, 100.0)}%</b>.</p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Behavioral Change Intent")
    pivot = st.radio("Based on this insight, I intend to:", ["Reduce UberEats spending", "Seek cheaper housing", "Make no changes"])
    
    if st.button("FINISH & SAVE SESSION"):
        st.session_state.step = "home"
        st.rerun()

st.markdown('<div style="text-align:center; color:#94A3B8; padding:40px;">Lead Researcher: Sandeep Sharma | Excelsia College</div>', unsafe_allow_html=True)
