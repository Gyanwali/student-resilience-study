import streamlit as st
import gspread
import math
import plotly.express as px
import plotly.graph_objects as go
import random
import time
from datetime import datetime, timedelta

# --- 1. SECURE DATABASE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"

def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_info)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception:
        return None

# --- 2. ENLIGHTENED AI ENGINE ---
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
    runway = round(savings / m_exp, 1) if m_exp > 0 else 0.0
    
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
        "rent_pct": round((exp_vals["Housing (Rent)"] / m_inc) * 100, 1),
        "uber_pct": round((exp_vals["Lifestyle (Uber)"] / m_inc) * 100, 1),
        "m_inc": m_inc,
        "m_exp": m_exp,
        "exp_breakdown": exp_vals
    }

# --- 3. PREMIUM RESEARCH UI ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .metric-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); 
                   padding: 20px; border-radius: 15px; text-align: center; }
    .ai-bubble { background: rgba(37, 99, 235, 0.08); border-left: 5px solid #2563EB; padding: 20px; 
                 border-radius: 12px; margin: 20px 0; line-height: 1.6; font-size: 1.1rem; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #2563EB !important; 
                       color: white !important; font-weight: bold; }
    h1, h2, h3 { color: #2563EB; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "finished":
    st.balloons()
    st.title("✅ Research Entry Secured")
    st.markdown(f'<div class="ai-bubble"><b>Thank you!</b> Your data (ID: {st.session_state.get("last_id")}) has been added to the Sydney Student Resilience dataset. You may now close this tab.</div>', unsafe_allow_html=True)
    st.stop()

if st.session_state.step == "home":
    st.title("🛡️ Resilience Intelligence Lab")
    st.markdown("### Sydney Student Research Study")
    st.info("This AI evaluates your 'Financial Shock Absorption'—your ability to survive economic changes in Sydney.")
    if st.checkbox("I consent to participate in this anonymized study."):
        if st.button("INITIALIZE AI DIAGNOSTIC"):
            st.session_state.participant_id = f"RES-{random.randint(10000, 99999)}"
            st.session_state.step = "inputs"
            st.rerun()

elif st.session_state.step == "inputs":
    st.subheader(f"📍 Session ID: {st.session_state.participant_id}")
    with st.form("data_entry"):
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield", "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
        addr = st.selectbox("Current Suburb", suburbs)
        custom_sub = st.text_input("If 'Other', type here:")
        final_addr = custom_sub if addr == "Other" else addr
        
        c1, c2 = st.columns(2)
        inc = c1.number_input("Monthly Income ($)", 500, 10000, 3200)
        rent = c2.number_input("Weekly Rent ($)", 100, 1500, 450)
        uber = st.slider("Weekly Lifestyle/UberEats ($)", 0, 800, 120)
        
        with st.expander("Secondary Resilience Metrics"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Access to Emergency Family Support?", ["No", "Yes"])
            p_amt = st.number_input("Monthly Support Available ($)", 0, 5000, 0)
            savings = st.number_input("Total Emergency Savings ($)", 0, 50000, 2000)
            groc = st.number_input("Weekly Groceries ($)", 0, 500, 140)
            trans = st.number_input("Weekly Transport ($)", 0, 300, 45)
            bills = st.number_input("Monthly Utilities/Bills ($)", 0, 800, 150)
            remit = st.number_input("Monthly Remittance Sent Home ($)", 0, 3000, 0)
            months = st.number_input("Months Living in Sydney", 1, 120, 12)
            meals = st.radio("Have you skipped meals to save money?", ["No", "Yes"])

        if st.form_submit_button("GENERATE ENLIGHTENED REPORT"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": final_addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                sydney_time = datetime.utcnow() + timedelta(hours=11)
                row = [sydney_time.strftime("%Y-%m-%d %H:%M"), st.session_state.participant_id, rent, inc, final_addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row)
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.title("📊 Enlightened Resilience Report")
    
    # INFOGRAPHIC 1: METRIC GRID
    col1, col2, col3 = st.columns(3)
    col1.markdown(f'<div class="metric-card"><h3>{ai["score"]}</h3>Resilience Score</div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><h3>{ai["runway"]}</h3>Survival Mo.</div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><h3>{ai["prob"]}%</h3>Success Rate</div>', unsafe_allow_html=True)

    # INFOGRAPHIC 2: GAUGE CHART
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = ai['score'],
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Resilience Health Index", 'font': {'size': 20}},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#2563EB"}}
    ))
    fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # AI EXPLANATION
    st.markdown(f"""
    <div class="ai-bubble">
    <b>🤖 Deep Analysis for {st.session_state.participant_id}:</b><br><br>
    Your housing load in <b>{st.session_state.data['addr']}</b> consumes <b>{ai['rent_pct']}%</b> of your total income. 
    In Sydney, exceeding 30% is classified as "Rental Stress."<br><br>
    <b>Survival Runway:</b> If your income stopped today, your savings would last <b>{ai['runway']} months</b>. 
    Your surplus is <b>${ai['m_surplus']}</b>. Increasing this by reducing lifestyle spending (currently {ai['uber_pct']}% of income) 
    is your fastest path to a higher resilience score.
    </div>
    """, unsafe_allow_html=True)

    # INFOGRAPHIC 3: EXPENSE PIE
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), 
                     title="Monthly Expenditure Breakdown", hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig_pie, use_container_width=True)

    # FINAL SYNC FORM
    with st.form("final_eval"):
        st.subheader("🎯 Research Validation")
        trust = st.select_slider("Do you trust the AI logic?", options=["Low", "Neutral", "High"])
        useful = st.select_slider("Is this report enlightening?", options=["No", "Neutral", "Yes"])
        intent = st.radio("Next Action:", ["Reduce Spending", "Search Cheaper Housing", "No Change"])
        
        if st.form_submit_button("SUBMIT & LOCK DATA"):
            sheet = connect_to_sheet()
            if sheet:
                try:
                    cell = sheet.find(st.session_state.participant_id)
                    sheet.update_cell(cell.row, 7, trust)
                    sheet.update_cell(cell.row, 8, useful)
                    sheet.update_cell(cell.row, 18, intent)
                    st.session_state.last_id = st.session_state.participant_id
                    st.session_state.step = "finished"
                    st.rerun()
                except:
                    st.error("Sync error. Please try once more.")
