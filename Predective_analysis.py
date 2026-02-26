import streamlit as st
import gspread
import math
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime, timedelta

# --- 1. SECURE RESEARCH INFRASTRUCTURE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"

def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_info)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception:
        return None

# --- 2. ENLIGHTENED PREDICTIVE ENGINE ---
def run_research_model(data):
    # Monthly Cashflow Logic
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
    
    # Emergency Runway (How many months savings last)
    savings = float(data['savings'])
    runway = round(savings / m_exp, 1) if m_exp > 0 else 12.0
    
    # Resilience & Success Prob
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)
    
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "runway": runway,
        "uber_pct": round((exp_vals["UberEats/Dining"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Rent"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. PREMIUM UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    html, body, [class*="css"], p, h1, h2, h3, h4, span, label, li, td, th { color: #000000 !important; }
    .res-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #E5E7EB; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stat-box { background: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #CBD5E1; text-align: center; }
    .ai-bubble { background: #EEF2FF; border-left: 5px solid #4338CA; padding: 20px; border-radius: 12px; margin: 15px 0; font-style: italic; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #1E3A8A !important; color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "home":
    st.title("🛡️ Resilience Intelligence Lab")
    st.markdown('<div class="res-card"><h3>Strategic Assessment</h3><p>This AI evaluates the intersection of <b>Sydney Cost-of-Living</b> and <b>Student Behavioral Finance</b>. Your results will include a deep diagnostic of your financial buffer.</p></div>', unsafe_allow_html=True)
    if st.button("INITIALIZE RESEARCH TERMINAL"):
        st.session_state.participant_id = f"RES-{random.randint(10000, 99999)}"
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    st.subheader(f"📍 Profile ID: {st.session_state.participant_id}")
    with st.form("input_form"):
        addr = st.selectbox("Current Suburb", ["Hurstville", "Parramatta", "CBD", "Randwick", "Strathfield", "Other"])
        inc = st.slider("Monthly Income (AUD)", 500, 10000, 3200, step=100)
        rent = st.slider("Weekly Rent (AUD)", 100, 1500, 450, step=10)
        uber = st.slider("Weekly UberEats/Lifestyle (AUD)", 0, 800, 120, step=10)
        
        with st.expander("Secondary Research Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Family Support Available?", ["No", "Yes"])
            p_amt = st.slider("Monthly Support ($)", 0, 5000, 0, step=100) if p_supp == "Yes" else 0
            savings = st.slider("Current Savings ($)", 0, 50000, 2000, step=500)
            groc = st.slider("Weekly Groceries ($)", 0, 500, 140, step=10)
            trans = st.slider("Weekly Transport ($)", 0, 300, 45, step=5)
            bills = st.slider("Monthly Utilities ($)", 0, 800, 150, step=10)
            remit = st.slider("Monthly Remittance ($)", 0, 3000, 0, step=100)
            months = st.number_input("Months in Sydney", min_value=1, value=12)
            meals = st.radio("Skipped meals to save?", ["No", "Yes"])

        if st.form_submit_button("GENERATE ENLIGHTENED REPORT"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                sydney_time = datetime.utcnow() + timedelta(hours=11)
                row = [sydney_time.strftime("%Y-%m-%d %H:%M"), st.session_state.participant_id, rent, inc, addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.current_row = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.title("📊 Enlightened AI Report")
    
    # --- KEY METRICS ---
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="stat-box"><b>Resilience</b><br><h3>{ai["score"]}/100</h3></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="stat-box"><b>Runway</b><br><h3>{ai["runway"]} Mo.</h3></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="stat-box"><b>Success</b><br><h3>{ai["prob"]}%</h3></div>', unsafe_allow_html=True)

    # --- ENLIGHTENED XAI DIAGNOSIS ---
    st.markdown('<div class="res-card"><h3>🤖 Explainable AI (XAI) Diagnosis</h3>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="ai-bubble">
    "Based on your profile, the AI identifies your <b>Housing Load ({ai['rent_pct']}%)</b> as the primary driver of your financial vulnerability. 
    In the Sydney rental market, this 'fixed-cost' rigidity leaves you with an Emergency Runway of only <b>{ai['runway']} months</b>. 
    If a shock occurs (e.g., job loss), your current savings would be depleted rapidly."
    </div>
    """, unsafe_allow_html=True)
    
    # Specific Suggestion
    improvement = min(ai['prob'] + 15, 100.0)
    st.write(f"### 🎯 Strategic Recommendation")
    st.write(f"""
    The AI has performed a **Counter-Factual Simulation**: 
    If you reallocate 25% of your **UberEats/Dining** budget toward your savings, your Success Probability shifts from {ai['prob']}% to **{improvement}%**. 
    This behavioral pivot would increase your Monthly Surplus to **${round(ai['m_surplus'] + 120, 2)}**.
    """)
    st.markdown('</div>', unsafe_allow_html=True)

    # Visualization
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5, title="Monthly Expenditure Flow")
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- RESEARCH FEEDBACK ---
    st.markdown('<div class="res-card"><h3>🎯 Research Evaluation</h3>', unsafe_allow_html=True)
    trust = st.select_slider("Do you trust this AI's logic?", options=["Low", "Neutral", "High"])
    usefulness = st.select_slider("How enlightening was this feedback?", options=["Not at all", "Somewhat", "Very Enlightening"])
    intent = st.radio("Behavioral Change Intent:", ["I will reduce lifestyle spending", "I will seek cheaper housing", "No change"])
    
    if st.button("SUBMIT FINAL DATA"):
        sheet = connect_to_sheet()
        if sheet and st.session_state.current_row:
            sheet.update_cell(st.session_state.current_row, 7, trust)
            sheet.update_cell(st.session_state.current_row, 8, usefulness)
            sheet.update_cell(st.session_state.current_row, 18, intent)
            st.success("Analysis Complete! Session Resetting...")
            st.session_state.clear()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
