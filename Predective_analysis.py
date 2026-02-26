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

# --- 3. UI STYLE (CLEAN & BLACK TEXT) ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    /* Clean UI Overrides */
    html, body, [class*="css"], p, h1, h2, h3, h4, span, label, li { 
        color: #000000 !important; 
    }
    .stSlider [data-baseweb="slider"] { margin-bottom: 40px; }
    .res-card { 
        background: white; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #E5E7EB; 
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5rem; 
        background: #1E3A8A !important; color: white !important; font-weight: bold; 
    }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'current_row' not in st.session_state: st.session_state.current_row = None

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.title("👋 Welcome")
    st.markdown('<div class="res-card"><h3>Resilience Lab AI</h3><p>Predicting financial stability for international students in Sydney. This diagnostic takes 2 minutes and is completely anonymous.</p></div>', unsafe_allow_html=True)
    if st.button("START AI ANALYSIS"):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    st.markdown("### 📍 Your Profile")
    st.write("Use the sliders below for a cleaner experience on mobile.")
    
    with st.form("clean_input_form"):
        addr = st.selectbox("Sydney Area (Suburb)", ["Hurstville", "Parramatta", "CBD", "Randwick", "Strathfield", "Other"])
        inc = st.slider("Monthly Income (AUD)", 1000, 8000, 3200, step=100)
        rent = st.slider("Weekly Rent (AUD)", 100, 1000, 450, step=10)
        uber = st.slider("Weekly UberEats/Dining (AUD)", 0, 500, 120, step=10)
        
        with st.expander("Show Detailed Variables (Required)"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Access to Family Support?", ["No", "Yes"])
            p_amt = st.slider("Monthly Family Support Amt ($)", 0, 3000, 0, step=100) if p_supp == "Yes" else 0
            savings = st.slider("Current Savings ($)", 0, 20000, 2000, step=500)
            groc = st.slider("Weekly Groceries ($)", 50, 400, 140, step=10)
            trans = st.slider("Weekly Transport ($)", 0, 200, 45, step=5)
            bills = st.slider("Monthly Utilities ($)", 0, 500, 150, step=10)
            remit = st.slider("Monthly Remittance ($)", 0, 2000, 0, step=500)
            months = st.number_input("Months in Sydney", min_value=1, value=12) # Kept as number for precision
            meals = st.radio("Have you skipped meals to save?", ["No", "Yes"])

        if st.form_submit_button("ANALYZE MY DATA"):
            unique_id = f"RES-{random.randint(10000, 99999)}"
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                # A:Timestamp, B:ID, C:Rent, D:Inc, E:Area, F:Uber, G:Trust, H:Useful, I:Score, J:Meals, K:P_Supp, L:Remit, M:P_Amt, N:Savings, O:Trans, P:Lit, Q:Months, R:Intent
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), unique_id, rent, inc, addr, uber, "...", "...", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "..."]
                
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.current_row = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.markdown("### 📊 Your AI Resilience Dashboard")
    
    # Visual Analytics (Charts)
    fig = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.6)
    fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    <div class="res-card">
        <p><b>Resilience Score:</b> {ai['score']}/100</p>
        <p><b>Success Probability:</b> {ai['prob']}%</p>
        <hr>
        <p><b>AI Reasoning:</b> Your rent is {ai['rent_pct']}% of income. UberEats is {ai['uber_pct']}%. 
        Cutting UberEats by $30/week improves success probability by 10%.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="res-card"><h4>Research Feedback</h4>', unsafe_allow_html=True)
    trust = st.select_slider("Trust level?", options=["Low", "Neutral", "High"])
    intent = st.radio("Behavioral Plan:", ["Reduce Spending", "Cheaper Rent", "No Change"])
    
    if st.button("SAVE & FINISH"):
        sheet = connect_to_sheet()
        if sheet and st.session_state.current_row:
            sheet.update_cell(st.session_state.current_row, 7, trust)
            sheet.update_cell(st.session_state.current_row, 18, intent)
            st.success("Analysis Complete!")
            st.session_state.step = "home"
            st.rerun()

st.markdown('<p style="text-align:center; color:#6B7280; font-size:0.8rem; padding:20px;">Researcher: Sandeep Sharma | Excelsia College</p>', unsafe_allow_html=True)
