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
        "Housing (Rent)": float(data['rent']) * 4.33,
        "Groceries": float(data['groc']) * 4.33,
        "Discretionary (UberEats)": float(data['uber']) * 4.33,
        "Transport": float(data['trans']) * 4.33,
        "Fixed Bills": float(data['bills']),
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
        "uber_pct": round((exp_vals["Discretionary (UberEats)"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Housing (Rent)"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .res-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .insight-box { background: #F1F5F9; border-left: 5px solid #2563EB; padding: 15px; border-radius: 8px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'row_idx' not in st.session_state: st.session_state.row_idx = None

# --- 4. NAVIGATION ---

# PAGE 1: CONSENT GATEKEEPER
if st.session_state.step == "home":
    st.title("👋 Welcome to Resilience Lab")
    st.markdown('<div class="res-card"><h3>Participant Consent Form</h3><p>By participating in this study, you acknowledge that your financial data will be analyzed anonymously for research purposes. You are free to withdraw at any time.</p></div>', unsafe_allow_html=True)
    
    consent_check = st.checkbox("I have read the briefing and I CONSENT to participate in this study.")
    
    if st.button("START MY AI DIAGNOSTIC", use_container_width=True):
        if consent_check:
            st.session_state.step = "inputs"
            st.rerun()
        else:
            st.warning("⚠️ You must provide consent to proceed with the research.")

# PAGE 2: DATA INPUTS (Your friend enters data here)
elif st.session_state.step == "inputs":
    with st.form("input_form"):
        st.subheader("📍 Current Lifestyle Details")
        addr = st.text_input("Sydney Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        inc = st.number_input("Monthly Income ($)", value=3200)
        p_supp = st.radio("Family Support Available?", ["No", "Yes"])
        p_amt = st.number_input("Monthly Support ($)", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Total Savings ($)", value=2000)
        rent = st.number_input("Weekly Rent ($)", value=450)
        uber = st.number_input("Weekly UberEats/Dining ($)", value=120)
        groc = st.number_input("Weekly Groceries ($)", value=140)
        trans = st.number_input("Weekly Transport ($)", value=45)
        bills = st.number_input("Monthly Bills ($)", value=150)
        remit = st.number_input("Monthly Remittance ($)", value=0)
        months = st.number_input("Months in Sydney", value=12)
        meals = st.radio("Have you skipped meals to save?", ["No", "Yes"])

        if st.form_submit_button("ANALYZE & SYNC TO RESEARCH DATABASE", use_container_width=True):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                # Map to A-R (18 Columns)
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), "Yes", rent, inc, addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.row_idx = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

# PAGE 3: THE DEEP EXPLANATION DASHBOARD
elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.header("📊 AI Resilience Report")
    
    st.markdown('<div class="res-card"><h3>🤖 AI Deep Reasoning (XAI)</h3>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="insight-box">
    <b>Score: {ai['score']}/100</b> | <b>Success Prob: {ai['prob']}%</b>
    </div>
    <p><b>Analysis:</b> Your rent accounts for <b>{ai['rent_pct']}%</b> of your income. UberEats habits consume <b>{ai['uber_pct']}%</b>.
    The AI predicts that a 20% reduction in discretionary spending will improve your score by 15 points.</p>
    """, unsafe_allow_html=True)
    
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5)
    fig_pie.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # PAGE 4: BEHAVIORAL FEEDBACK (The "Last Question")
    st.markdown('<div class="res-card"><h3>🎯 Behavioral Pivot</h3>', unsafe_allow_html=True)
    trust = st.select_slider("Do you trust this AI score?", options=["Low", "Neutral", "High"], value="Neutral")
    useful = st.select_slider("How useful was this feedback?", options=["Low", "Medium", "High"], value="Medium")
    intent = st.radio("Based on this prediction, what is your next step?", ["Reduce UberEats spending", "Look for cheaper housing", "No changes"])
    
    if st.button("SUBMIT FINAL FEEDBACK", use_container_width=True):
        sheet = connect_to_sheet()
        if sheet and st.session_state.row_idx:
            sheet.update_cell(st.session_state.row_idx, 7, trust)
            sheet.update_cell(st.session_state.row_idx, 8, useful)
            sheet.update_cell(st.session_state.row_idx, 18, intent)
            st.success("Session complete. Your data has been recorded for analysis.")
            st.session_state.step = "home"
            st.rerun()

st.markdown('<div style="text-align:center; color:#94A3B8; padding:30px;">Researcher: Sandeep Sharma | Excelsia College</div>', unsafe_allow_html=True)
