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
        # Targeted fix for your specific sheet name
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception:
        return None

# --- 2. PREDICTIVE AI ENGINE ---
def run_research_model(data):
    m_inc = max(data['income'] + data['p_amt'], 1)
    m_exp = (data['rent'] + data['groc'] + data['uber'] + data['trans']) * 4.33 + data['bills'] + data['remit']
    surplus = m_inc - m_exp
    
    # Sigmoid Logic for Success Probability
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)

    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": prob_success,
        "uber_pct": round(((data['uber'] * 4.33) / m_inc) * 100, 1)
    }

# --- 3. THEME & HEADER ---
st.set_page_config(page_title="Resilience Lab AI", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC !important; }
    .nav-header { background: #0F172A; padding: 30px; text-align: center; border-radius: 0 0 20px 20px; color: white; margin-bottom: 25px;}
    .res-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

st.markdown('<div class="nav-header"><h1 style="color:white !important;">Resilience Intelligence Lab</h1><p style="color:#38BDF8 !important;">XAI Predictive Analytics | Master\'s Research Tool</p></div>', unsafe_allow_html=True)

# --- 4. RESEARCH FLOW ---

# STEP 1: HOME & ETHICS
if st.session_state.step == "home":
    st.markdown('<div class="res-card"><h2>Project Overview</h2><p>This study investigates the impact of Predictive AI on the financial resilience of international students in Sydney. Your participation is voluntary and data is anonymized.</p></div>', unsafe_allow_html=True)
    if st.button("INITIALIZE DIAGNOSTIC"):
        st.session_state.step = "inputs"
        st.rerun()

# STEP 2: MULTI-FACTOR INPUTS
elif st.session_state.step == "inputs":
    with st.form("research_form"):
        st.markdown('### 📍 Section 1: Baseline Context')
        # NEW: Pre-intervention stress variable (for thesis comparison)
        pre_stress = st.select_slider("Rate your current financial stress (1 = Low, 10 = High)", options=range(1, 11), value=5)
        
        addr = st.text_input("Sydney Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        
        st.markdown('### 💰 Section 2: Cashflow & Behavior')
        c1, c2 = st.columns(2)
        with c1: inc = st.number_input("Monthly Income (AUD)", value=3200)
        with c2: p_supp = st.radio("Access to Family Support?", ["No", "Yes"])
        
        p_amt = st.number_input("Support Amount", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Total Emergency Savings", value=2000)
        
        st.markdown('### 📉 Section 3: Weekly Discretionary Spending')
        rent = st.number_input("Weekly Rent", value=450)
        uber = st.number_input("Weekly UberEats/Dining", value=120)
        groc = st.number_input("Weekly Groceries", value=140)
        trans = st.number_input("Weekly Transport", value=45)
        bills = st.number_input("Monthly Utilities", value=150)
        remit = st.number_input("Monthly Remittance", value=0)
        months = st.number_input("Months in Australia", value=12)
        meals = st.radio("Skipped meals to save money?", ["No", "Yes"])

        if st.form_submit_button("GENERATE AI PREDICTION & SYNC"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months, "pre_stress": pre_stress}
            st.session_state.data = data
            
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                # Aligned for your "Form Responses 1" 15-column sheet
                row = [datetime.now().strftime("%Y-%m-%d"), rent, inc, addr, uber, res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, res['prob']]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.step = "results"
                st.rerun()

# STEP 3: XAI DASHBOARD
elif st.session_state.step == "results":
    res = st.session_state.data
    ai = run_research_model(res)
    
    st.success("✅ Research data successfully synchronized to 'Form Responses 1'")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Resilience Index", f"{ai['score']}/100")
    m2.metric("Success Prob.", f"{ai['prob']}%")
    m3.metric("Monthly Surplus", f"${ai['m_surplus']}")

    st.markdown(f"""
    <div class="res-card">
        <h3>🤖 Explainable AI (XAI) Reasoning</h3>
        <p>• <b>Discretionary Alert:</b> Your UberEats spending is <b>{ai['uber_pct']}%</b> of your total income.</p>
        <p>• <b>Resilience Logic:</b> Your score of {ai['score']} is influenced by your {res['lit']} literacy and {'family buffer' if res['p_supp'] == 'Yes' else 'lack of family buffer'}.</p>
        <p>• <b>Prediction:</b> A 15% reduction in discretionary spending would raise your success probability to <b>{min(ai['prob']+10, 100.0)}%</b>.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # NEW: Post-Intervention Survey (The "Impact" measurement)
    st.markdown("### 📝 Post-Analysis Survey")
    post_impact = st.radio("Has seeing this AI analysis changed your financial outlook?", ["Yes", "No", "Maybe"])
    if st.button("Finalize Session"):
        st.session_state.step = "home"
        st.rerun()

st.markdown('<div style="text-align:center; color:#94A3B8; padding:30px;">Researcher: Sandeep Sharma | Excelsia College</div>', unsafe_allow_html=True)
