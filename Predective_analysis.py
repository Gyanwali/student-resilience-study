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

# --- 2. ENLIGHTENED PREDICTIVE ENGINE ---
def run_research_model(data):
    # Prevent Division by Zero
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    
    exp_vals = {
        "Housing (Rent)": float(data['rent']) * 4.33,
        "Food (Groc)": float(data['groc']) * 4.33,
        "Lifestyle (Uber)": float(data['uber']) * 4.33,
        "Transport": float(data['trans']) * 4.33,
        "Fixed Bills": float(data['bills']),
        "Remittance": float(data['remit'])
    }
    m_exp = max(sum(exp_vals.values()), 1.0)
    surplus = m_inc - m_exp
    
    # Runway Calculation
    savings = float(data['savings'])
    runway = round(savings / m_exp, 1) if savings > 0 else 0.0
    
    # Success Probability (Sigmoid)
    z = (surplus / m_exp) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)
    
    # Resilience Scoring
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "runway": runway,
        "rent_pct": round((exp_vals["Housing (Rent)"] / m_inc) * 100, 1),
        "uber_pct": round((exp_vals["Lifestyle (Uber)"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. DYNAMIC UI STYLE ---
st.set_page_config(page_title="Resilience Lab", layout="centered")
st.markdown("""
<style>
    .res-card { padding: 25px; border-radius: 18px; border: 1px solid rgba(128, 128, 128, 0.2); 
                margin-bottom: 20px; background: rgba(128, 128, 128, 0.08); backdrop-filter: blur(10px); }
    .ai-bubble { background: rgba(37, 99, 235, 0.1); border-left: 5px solid #2563EB; padding: 18px; 
                 border-radius: 12px; margin: 15px 0; font-family: 'Inter', sans-serif; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #2563EB !important; 
                       color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "home":
    st.title("🛡️ Resilience Intelligence Lab")
    st.markdown('<div class="res-card"><h3>Participant Briefing</h3><p>This study uses <b>Explainable AI (XAI)</b> to evaluate financial shock-absorption for students in Sydney. Your inputs generate a unique research record.</p></div>', unsafe_allow_html=True)
    consent = st.checkbox("I consent to participate in this study.")
    if st.button("INITIALIZE TERMINAL"):
        if consent:
            st.session_state.participant_id = f"RES-{random.randint(10000, 99999)}"
            st.session_state.step = "inputs"
            st.rerun()
        else: st.error("Consent is required.")

elif st.session_state.step == "inputs":
    st.subheader(f"📍 Research Profile: {st.session_state.participant_id}")
    with st.form("input_form"):
        # Universal Suburb Logic
        addr_list = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield", "Burwood", "Auburn", "Other"])
        addr_choice = st.selectbox("Current Suburb", addr_list)
        custom_sub = st.text_input("If 'Other', type here:")
        final_addr = custom_sub if addr_choice == "Other" else addr_choice
        
        inc = st.slider("Monthly Income ($)", 500, 10000, 3200)
        rent = st.slider("Weekly Rent ($)", 100, 1500, 450)
        uber = st.slider("Weekly Lifestyle/Uber ($)", 0, 800, 120)
        
        with st.expander("Secondary Research Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Family Support Available?", ["No", "Yes"])
            p_amt = st.slider("Monthly Support ($)", 0, 5000, 0)
            savings = st.slider("Current Savings ($)", 0, 50000, 2000)
            groc = st.slider("Weekly Groceries ($)", 0, 500, 140)
            trans = st.slider("Weekly Transport ($)", 0, 300, 45)
            bills = st.slider("Monthly Utilities ($)", 0, 800, 150)
            remit = st.slider("Monthly Remittance ($)", 0, 3000, 0)
            months = st.number_input("Months in Sydney", min_value=1, value=12)
            meals = st.radio("Skipped meals to save?", ["No", "Yes"])

        if st.form_submit_button("GENERATE ENLIGHTENED REPORT"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": final_addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                # SYDNEY TIMEZONE OFFSET
                sydney_time = datetime.utcnow() + timedelta(hours=11)
                # Sync Stage 1: Append New User Row
                row = [sydney_time.strftime("%Y-%m-%d %H:%M"), st.session_state.participant_id, rent, inc, final_addr, uber, "...", "...", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "..."]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    st.title("📊 Enlightened AI Report")
    
    # Dashboard Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Resilience Score", f"{ai['score']}/100")
    c2.metric("Survival Runway", f"{ai['runway']} Mo.")
    c3.metric("Success Prob.", f"{ai['prob']}%")

    # XAI Detailed Explanation
    st.markdown('<div class="res-card"><h3>🤖 AI Deep Reasoning</h3>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="ai-bubble">
    <b>Analysis:</b> Your housing burden is <b>{ai['rent_pct']}%</b> of income. 
    In the Sydney market, this high 'fixed-cost' creates <i>Financial Rigidity</i>. 
    <br><br>
    <b>Prediction:</b> If discretionary spending (UberEats) is reduced by 25%, your success probability shifts from {ai['prob']}% to <b>{min(ai['prob']+14, 100.0)}%</b>. 
    Your surplus of <b>${ai['m_surplus']}</b> acts as your primary buffer against inflation.
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Final Feedback (Sync Stage 2)
    st.markdown('<div class="res-card"><h3>🎯 Evaluation</h3>', unsafe_allow_html=True)
    trust = st.select_slider("Trust level?", options=["Low", "Neutral", "High"])
    useful = st.select_slider("Is this enlightening?", options=["No", "Neutral", "Yes"])
    intent = st.radio("Behavioral Intent:", ["Reduce spending", "Cheaper rent", "No change"])
    
    if st.button("SUBMIT FINAL FEEDBACK"):
        sheet = connect_to_sheet()
        if sheet:
            try:
                cell = sheet.find(st.session_state.participant_id)
                sheet.update_cell(cell.row, 7, trust)   # Col G
                sheet.update_cell(cell.row, 8, useful)  # Col H
                sheet.update_cell(cell.row, 18, intent) # Col R
                st.success("Research Entry Secured.")
                st.session_state.clear()
                st.rerun()
            except:
                st.error("Error updating feedback. Data still saved in initial row.")
