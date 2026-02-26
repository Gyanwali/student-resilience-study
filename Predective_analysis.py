import streamlit as st
import gspread
import math
import plotly.express as px
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

# --- 2. THE PREDICTIVE ENGINE ---
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

# --- 3. PREMIUM MOBILE CSS ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F9FAFB; }
    
    .main-header { background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); padding: 40px 20px; text-align: center; border-radius: 0 0 30px 30px; color: white; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .res-card { background: white; padding: 25px; border-radius: 20px; border: 1px solid #E5E7EB; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .stat-val { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; line-height: 1; }
    .stat-lab { font-size: 0.85rem; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .insight-pill { background: #EFF6FF; color: #1E40AF; padding: 12px 18px; border-radius: 12px; border-left: 4px solid #3B82F6; margin: 10px 0; font-size: 0.95rem; line-height: 1.5; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #1E3A8A !important; color: white !important; font-weight: 700; border: none; transition: all 0.3s ease; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'row_idx' not in st.session_state: st.session_state.row_idx = None

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.markdown('<div class="main-header"><h1>Resilience Lab</h1><p>Predictive AI Financial Diagnostic</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="res-card"><h3>Participant Consent</h3><p>This AI model predicts financial resilience based on discretionary spending behavior. By clicking start, you consent to anonymized data collection.</p></div>', unsafe_allow_html=True)
    if st.button("BEGIN DIAGNOSTIC"):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    st.markdown("### 📝 Financial Profile")
    with st.form("input_form"):
        addr = st.text_input("Current Suburb", value="Hurstville")
        inc = st.number_input("Monthly Income ($)", value=3200)
        rent = st.number_input("Weekly Rent ($)", value=450)
        uber = st.number_input("Weekly UberEats/Dining ($)", value=120)
        
        with st.expander("Additional Research Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Emergency Family Support?", ["No", "Yes"])
            p_amt = st.number_input("Support Amount ($)", value=0) if p_supp == "Yes" else 0
            savings = st.number_input("Emergency Savings ($)", value=2000)
            groc = st.number_input("Weekly Groceries ($)", value=140)
            trans = st.number_input("Weekly Transport ($)", value=45)
            bills = st.number_input("Monthly Bills ($)", value=150)
            remit = st.number_input("Monthly Remittance ($)", value=0)
            months = st.number_input("Months in Sydney", value=12)
            meals = st.radio("Skipped meals to save money?", ["No", "Yes"])

        if st.form_submit_button("ANALYZE MY DATA"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), "Yes", rent, inc, addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.row_idx = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    # Header Statistics
    st.markdown("### 📊 Your Resilience Intelligence")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="res-card"><p class="stat-lab">Resilience Score</p><p class="stat-val">{ai["score"]}%</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="res-card"><p class="stat-lab">Success Prob.</p><p class="stat-val">{ai["prob"]}%</p></div>', unsafe_allow_html=True)

    # XAI Explanation
    st.markdown('<div class="res-card"><h4>🤖 AI Explanation & Predictions</h4>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="insight-pill"><b>Rent Impact:</b> Your housing consumes <b>{ai['rent_pct']}%</b> of your income. In Sydney, keeping this under 30% is critical for long-term stability.</div>
    <div class="insight-pill"><b>Behavioral Leak:</b> Discretionary spending (UberEats) is currently <b>{ai['uber_pct']}%</b> of your budget.</div>
    <div class="insight-pill" style="background:#ECFDF5; border-color:#10B981; color:#065F46;"><b>AI Prediction:</b> Reducing UberEats by just <b>$40/week</b> improves your Resilience Score to <b>{min(ai['score']+12, 100)}%</b> and your monthly surplus to <b>${round(ai['m_surplus']+173, 2)}</b>.</div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Visualization
    st.markdown('<div class="res-card"><h4>Monthly Spending Breakdown</h4>', unsafe_allow_html=True)
    fig = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.6, color_discrete_sequence=px.colors.qualitative.Bold)
    fig.update_layout(showlegend=True, margin=dict(l=0, r=0, t=0, b=0), height=350)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Final Feedback
    st.markdown('<div class="res-card" style="border: 2px solid #1E3A8A;"><h4>Final Research Feedback</h4>', unsafe_allow_html=True)
    trust = st.select_slider("How much do you trust this score?", options=["Low", "Neutral", "High"], value="Neutral")
    useful = st.select_slider("Is this feedback useful?", options=["Not Useful", "Neutral", "Very Useful"], value="Neutral")
    intent = st.radio("Based on this AI, will you change your spending?", ["Yes, reduce UberEats", "Seek cheaper rent", "No changes"])
    
    if st.button("SUBMIT FINAL FEEDBACK"):
        sheet = connect_to_sheet()
        if sheet and st.session_state.row_idx:
            sheet.update_cell(st.session_state.row_idx, 7, trust)
            sheet.update_cell(st.session_state.row_idx, 8, useful)
            sheet.update_cell(st.session_state.row_idx, 18, intent)
            st.success("Research recorded! Thank you for your contribution.")
            st.session_state.step = "home"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<p style="text-align:center; color:#9CA3AF; font-size:0.8rem; margin-top:40px;">Researcher: Sandeep Sharma | Excelsia College</p>', unsafe_allow_html=True)
