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
    savings = float(data['savings'])
    runway = round(savings / m_exp, 1) if m_exp > 0 else 12.0
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
        "uber_pct": round((exp_vals["Lifestyle (Uber)"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Housing (Rent)"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. ADAPTIVE UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .res-card { padding: 25px; border-radius: 18px; border: 1px solid rgba(128, 128, 128, 0.2); 
                margin-bottom: 20px; background: rgba(128, 128, 128, 0.08); backdrop-filter: blur(10px); }
    .ai-bubble { background: rgba(37, 99, 235, 0.1); border-left: 5px solid #2563EB; padding: 18px; 
                 border-radius: 12px; margin: 15px 0; line-height: 1.6; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #2563EB !important; 
                       color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "home":
    st.title("🛡️ Resilience Intelligence Lab")
    st.markdown('<div class="res-card"><h3>Assessment Briefing</h3><p>Evaluates student financial resilience in Sydney. All data is saved anonymously for academic research.</p></div>', unsafe_allow_html=True)
    consent = st.checkbox("I consent to participate in this study.")
    if st.button("INITIALIZE TERMINAL"):
        if consent:
            st.session_state.participant_id = f"RES-{random.randint(10000, 99999)}"
            st.session_state.step = "inputs"
            st.rerun()
        else:
            st.error("Consent is required to proceed.")

elif st.session_state.step == "inputs":
    st.subheader(f"📍 Participant ID: {st.session_state.participant_id}")
    with st.form("input_form"):
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield", "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
        addr_choice = st.selectbox("Current Suburb", suburbs)
        custom_sub = st.text_input("If 'Other', type your suburb here:")
        final_addr = custom_sub if addr_choice == "Other" else addr_choice

        inc = st.slider("Monthly Income ($)", 500, 10000, 3200)
        rent = st.slider("Weekly Rent ($)", 100, 1500, 450)
        uber = st.slider("Weekly Lifestyle/Uber ($)", 0, 800, 120)
        
        with st.expander("Show More Research Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Family Support?", ["No", "Yes"])
            p_amt = st.slider("Monthly Support ($)", 0, 5000, 0)
            savings = st.slider("Current Savings ($)", 0, 50000, 2000)
            groc = st.slider("Weekly Groceries ($)", 0, 500, 140)
            trans = st.slider("Weekly Transport ($)", 0, 300, 45)
            bills = st.slider("Monthly Utilities ($)", 0, 800, 150)
            remit = st.slider("Monthly Remittance ($)", 0, 3000, 0)
            months = st.number_input("Months in Sydney", min_value=1, value=12)
            meals = st.radio("Skipped meals to save?", ["No", "Yes"])

        if st.form_submit_button("GENERATE XAI REPORT"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": final_addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                sydney_time = datetime.utcnow() + timedelta(hours=11)
                # Initial Append to Column A-R
                row = [sydney_time.strftime("%Y-%m-%d %H:%M"), st.session_state.participant_id, rent, inc, final_addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.title("📊 Enlightened AI Report")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Resilience", f"{ai['score']}/100")
    col2.metric("Runway", f"{ai['runway']} Mo.")
    col3.metric("Success", f"{ai['prob']}%")

    st.markdown('<div class="res-card"><h3>🤖 Explainable AI Diagnosis</h3>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="ai-bubble">
    <b>Analysis:</b> Your housing load is <b>{ai['rent_pct']}%</b> of income. 
    Your emergency survival runway is <b>{ai['runway']} months</b>. 
    <b>Recommendation:</b> A 20% reduction in lifestyle spending improves your success probability to <b>{min(ai['prob']+12, 100.0)}%</b>.
    </div>
    """, unsafe_allow_html=True)
    
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="res-card"><h3>🎯 Evaluation</h3>', unsafe_allow_html=True)
    trust = st.select_slider("Trust level?", options=["Low", "Neutral", "High"])
    useful = st.select_slider("Is this enlightening?", options=["No", "Neutral", "Yes"])
    intent = st.radio("Behavioral Intent:", ["Reduce spending", "Cheaper rent", "No change"])
    
    if st.button("SUBMIT FINAL FEEDBACK"):
        sheet = connect_to_sheet()
        if sheet:
            try:
                # Precision Search by Unique ID
                cell = sheet.find(st.session_state.participant_id)
                target_row = cell.row
                sheet.update_cell(target_row, 7, trust)   # Column G
                sheet.update_cell(target_row, 8, useful)  # Column H
                sheet.update_cell(target_row, 18, intent) # Column R
                st.success("Research Entry Secured.")
                st.session_state.clear()
                st.rerun()
            except:
                st.error("Submission error. Please try again.")
