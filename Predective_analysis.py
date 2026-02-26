import streamlit as st
import gspread
import math
import plotly.express as px
import random
from datetime import datetime

# --- 1. SECURE CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"

def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_info)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception:
        return None

# --- 2. PREDICTIVE ENGINE ---
def run_research_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    exp_vals = {
        "Rent": float(data['rent']) * 4.33,
        "Groceries": float(data['groc']) * 4.33,
        "UberEats/Dining": float(data['uber']) * 4.33,
        "Transport": float(data['trans']) * 4.33,
        "Bills": float(data['bills']),
        "Remittance": float(data['remit'])
    }
    m_exp = sum(exp_vals.values())
    surplus = m_inc - m_exp
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "uber_pct": round((exp_vals["UberEats/Dining"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Rent"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. UI STYLE (BLACK TEXT & MOBILE OPTIMIZED) ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    /* Force all text to black */
    html, body, [class*="css"], p, h1, h2, h3, h4, span, label { 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif;
    }
    .main-header { 
        background: #1E3A8A; 
        padding: 30px; 
        text-align: center; 
        border-radius: 15px; 
        margin-bottom: 20px; 
    }
    .main-header h1, .main-header p { color: white !important; }
    .res-card { 
        background: white; 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #000000; 
        margin-bottom: 15px; 
    }
    .stButton>button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3rem; 
        background: #1E3A8A !important; 
        color: white !important; 
    }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'current_row' not in st.session_state: st.session_state.current_row = None

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.markdown('<div class="main-header"><h1>Resilience Lab</h1><p>Predictive AI Financial Diagnostic</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="res-card"><h3>Consent</h3><p>By proceeding, you consent to anonymized data collection for Master\'s research at Excelsia College.</p></div>', unsafe_allow_html=True)
    if st.button("START DIAGNOSTIC"):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    st.markdown("### 📝 Enter Details")
    with st.form("input_form"):
        addr = st.text_input("Current Suburb", value="Hurstville")
        inc = st.number_input("Monthly Income ($)", value=3200)
        rent = st.number_input("Weekly Rent ($)", value=450)
        uber = st.number_input("Weekly UberEats ($)", value=120)
        
        with st.expander("More Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Family Support?", ["No", "Yes"])
            p_amt = st.number_input("Support Amount ($)", value=0) if p_supp == "Yes" else 0
            savings = st.number_input("Savings ($)", value=2000)
            groc = st.number_input("Weekly Groceries ($)", value=140)
            trans = st.number_input("Weekly Transport ($)", value=45)
            bills = st.number_input("Monthly Bills ($)", value=150)
            remit = st.number_input("Monthly Remittance ($)", value=0)
            months = st.number_input("Months in Sydney", value=12)
            meals = st.radio("Skipped meals?", ["No", "Yes"])

        if st.form_submit_button("ANALYZE & SAVE NEW ENTRY"):
            unique_id = f"RES-{random.randint(10000, 99999)}"
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                # A:Timestamp, B:Consent/ID, C:Rent, D:Inc, E:Area, F:Uber, G:Trust, H:Useful, I:Score, J:Meals, K:P_Supp, L:Remit, M:P_Amt, N:Savings, O:Trans, P:Lit, Q:Months, R:Intent
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), unique_id, rent, inc, addr, uber, "...", "...", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "..."]
                
                # append_row ensures a BRAND NEW row is created every time
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.current_row = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.markdown("### 📊 AI Resilience Dashboard")
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="res-card"><b>Score</b><br><span style="font-size:24px;">{ai["score"]}%</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="res-card"><b>Success Prob.</b><br><span style="font-size:24px;">{ai["prob"]}%</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="res-card"><h4>AI Insights</h4>', unsafe_allow_html=True)
    st.write(f"• Housing costs are **{ai['rent_pct']}%** of income.")
    st.write(f"• UberEats is **{ai['uber_pct']}%** of your budget.")
    st.write(f"• Predicted Surplus: **${ai['m_surplus']}**.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Visualization
    fig = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5)
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Last Question
    st.markdown('<div class="res-card"><h4>Final Research Feedback</h4>', unsafe_allow_html=True)
    trust = st.select_slider("Trust level?", options=["Low", "Neutral", "High"])
    intent = st.radio("Future Plan?", ["Reduce Spending", "Cheaper Rent", "No Change"])
    
    if st.button("FINISH & SYNC"):
        sheet = connect_to_sheet()
        if sheet and st.session_state.current_row:
            # Update the SPECIFIC row created for this user
            sheet.update_cell(st.session_state.current_row, 7, trust)
            sheet.update_cell(st.session_state.current_row, 18, intent)
            st.success("Entry Complete!")
            st.session_state.step = "home"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
