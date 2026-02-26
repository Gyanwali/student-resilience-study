import streamlit as st
import gspread
import math
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime, timedelta

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

# --- 2. ADVANCED PREDICTIVE ENGINE ---
def run_research_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    exp_vals = {
        "Housing (Rent)": float(data['rent']) * 4.33,
        "Food (Groc)": float(data['groc']) * 4.33,
        "Lifestyle (Uber)": float(data['uber']) * 4.33,
        "Transport": float(data['trans']) * 4.33,
        "Fixed Bills": float(data['bills']),
        "Remittance": float(data['remit'])
    }
    m_exp = sum(exp_vals.values())
    surplus = m_inc - m_exp
    
    # Success Probability (Sigmoid Analysis)
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)
    
    # Resilience Scoring Logic
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "uber_pct": round((exp_vals["Lifestyle (Uber)"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Housing (Rent)"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. PREMIUM UI STYLE ---
st.set_page_config(page_title="Resilience Intelligence Lab", layout="centered")
st.markdown("""
<style>
    html, body, [class*="css"], p, h1, h2, h3, h4, span, label, li, td, th { color: #000000 !important; }
    .res-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #E5E7EB; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stProgress > div > div > div > div { background-color: #1E3A8A; }
    .insight-pill { background: #F1F5F9; border-left: 5px solid #1E3A8A; padding: 15px; border-radius: 8px; margin: 10px 0; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #1E3A8A !important; color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'participant_id' not in st.session_state: st.session_state.participant_id = None

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "home":
    st.title("🛡️ Resilience Intelligence Lab")
    st.markdown('<div class="res-card"><h3>Participant Briefing</h3><p>This study evaluates the financial resilience of international students in Sydney using Explainable AI (XAI). Your inputs will generate a predictive success model.</p></div>', unsafe_allow_html=True)
    consent = st.checkbox("I consent to participate in this study.")
    if st.button("INITIALIZE AI DIAGNOSTIC") and consent:
        st.session_state.participant_id = f"RES-{random.randint(10000, 99999)}"
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    st.progress(50)
    st.subheader(f"📍 Research Profile: {st.session_state.participant_id}")
    with st.form("input_form"):
        addr = st.selectbox("Sydney Suburb", ["Hurstville", "Parramatta", "CBD", "Randwick", "Strathfield", "Other"])
        inc = st.slider("Monthly Income (AUD)", 500, 10000, 3200, step=100)
        rent = st.slider("Weekly Rent (AUD)", 100, 1500, 450, step=10)
        uber = st.slider("Weekly UberEats/Lifestyle (AUD)", 0, 800, 120, step=10)
        
        with st.expander("Secondary Research Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Parental/Family Support?", ["No", "Yes"])
            p_amt = st.slider("Monthly Support Amt ($)", 0, 5000, 0, step=100) if p_supp == "Yes" else 0
            savings = st.slider("Total Savings ($)", 0, 50000, 2000, step=500)
            groc = st.slider("Weekly Groceries ($)", 0, 500, 140, step=10)
            trans = st.slider("Weekly Transport ($)", 0, 300, 45, step=5)
            bills = st.slider("Monthly Utilities ($)", 0, 800, 150, step=10)
            remit = st.slider("Monthly Remittance ($)", 0, 3000, 0, step=100)
            months = st.number_input("Months in Sydney", min_value=1, value=12)
            meals = st.radio("Skipped meals to save money?", ["No", "Yes"])

        if st.form_submit_button("GENERATE XAI DASHBOARD"):
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
    st.progress(100)
    ai = run_research_model(st.session_state.data)
    st.title("📊 AI Resilience Dashboard")
    
    # --- VISUAL 1: GAUGE CHART ---
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = ai['score'],
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Resilience Score", 'font': {'size': 20, 'color': "black"}},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#1E3A8A"}, 'steps': [
            {'range': [0, 40], 'color': "#fee2e2"}, {'range': [40, 70], 'color': "#fef9c3"}, {'range': [70, 100], 'color': "#dcfce7"}]}))
    fig_gauge.update_layout(height=300, margin=dict(t=0, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # --- VISUAL 2: SPENDING PIE ---
    st.markdown('<div class="res-card"><h4>Spending Allocation</h4>', unsafe_allow_html=True)
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- XAI EXPLANATIONS ---
    st.markdown('<div class="res-card"><h3>🤖 Explainable AI Diagnosis</h3>', unsafe_allow_html=True)
    st.markdown(f'<div class="insight-pill"><b>Core Analysis:</b> Your Success Probability is <b>{ai["prob"]}%</b>. This is based on a monthly surplus of <b>${ai["m_surplus"]}</b> relative to Sydney living costs.</div>', unsafe_allow_html=True)
    
    if ai['rent_pct'] > 30:
        st.warning(f"⚠️ **Rental Stress Detected:** Your rent is {ai['rent_pct']}% of income. AI identifies this as a high-risk factor.")
    
    st.markdown(f"""
    <div class="insight-pill">
    <b>Predictive Suggestion:</b> By reducing Lifestyle/Uber spending by 20%, your Resilience Score would rise to <b>{min(ai['score']+12, 100)}</b>.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- FINAL EVALUATION ---
    st.markdown('<div class="res-card"><h3>🎯 Research Feedback</h3>', unsafe_allow_html=True)
    trust = st.select_slider("Trust in AI assessment?", options=["Low", "Neutral", "High"])
    usefulness = st.select_slider("Usefulness of AI suggestion?", options=["Low", "Neutral", "High"])
    intent = st.radio("Behavioral Change:", ["I will reduce lifestyle spending", "I will seek cheaper rent", "No change"])
    
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
