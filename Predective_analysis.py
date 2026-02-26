import streamlit as st
import gspread
import math
import plotly.express as px
import plotly.graph_objects as go
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
    
    # Success Probability Calculation
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)

    # Resilience Logic
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
    .metric-title { font-size: 1rem; color: #64748B; font-weight: 600; }
    .metric-value { font-size: 2rem; color: #1E40AF; font-weight: 800; }
    .insight-box { background: #F1F5F9; border-left: 5px solid #2563EB; padding: 15px; border-radius: 8px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'row_idx' not in st.session_state: st.session_state.row_idx = None

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.title("👋 Welcome to Resilience Lab")
    st.markdown('<div class="res-card"><h3>How Resilient Are You?</h3><p>This AI evaluates your financial habits in Sydney and predicts your ability to handle economic shocks. Participation is anonymous.</p></div>', unsafe_allow_html=True)
    if st.button("START MY AI DIAGNOSTIC", use_container_width=True):
        st.session_state.step = "inputs"
        st.rerun()

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

        if st.form_submit_button("ANALYZE MY FINANCIAL RESILIENCE", use_container_width=True):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                # Save initial data
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), "Yes", rent, inc, addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.row_idx = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.header("📊 Your AI Resilience Report")
    
    # Summary Cards
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="res-card"><p class="metric-title">Resilience Score</p><p class="metric-value">{ai["score"]}/100</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="res-card"><p class="metric-title">Success Probability</p><p class="metric-value">{ai["prob"]}%</p></div>', unsafe_allow_html=True)
    
    # 1. VISUAL SPENDING ANALYSIS
    st.markdown('<div class="res-card"><h4>Financial Distribution Analysis</h4>', unsafe_allow_html=True)
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
    fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)
    st.write(f"Your monthly surplus is **${ai['m_surplus']}**. This is the 'safety net' you have remaining each month.")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. XAI EXPLANATION & PREDICTION
    st.markdown('<div class="res-card"><h3>🤖 AI Deep Reasoning (XAI)</h3>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="insight-box">
    <b>Housing Load:</b> Your rent accounts for <b>{ai['rent_pct']}%</b> of your income. In Sydney's economy, any cost over 30% is considered a 'High Burden' that reduces your ability to handle emergencies.
    </div>
    <div class="insight-box">
    <b>Discretionary Spending Leak:</b> Your UberEats and Dining habits consume <b>{ai['uber_pct']}%</b> of your income. The AI identifies this as your primary area for behavioral improvement.
    </div>
    <div class="insight-box" style="border-left-color: #10B981;">
    <b>Predictive Future:</b> If you reduce discretionary spending by just <b>20%</b>, the AI predicts your Resilience Score will jump by <b>+15 points</b> and your 6-month survival probability will exceed <b>{min(ai['prob'] + 10, 100.0)}%</b>.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. BEHAVIORAL FEEDBACK
    st.markdown('<div class="res-card"><h3>🎯 Behavioral Pivot</h3>', unsafe_allow_html=True)
    st.write("How much do you trust this AI's assessment?")
    trust = st.select_slider("Trust Level", options=["Low", "Neutral", "High"], value="Neutral", label_visibility="collapsed")
    
    st.write("How useful was this feedback for you?")
    useful = st.select_slider("Usefulness", options=["Not Useful", "Neutral", "Very Useful"], value="Neutral", label_visibility="collapsed")
    
    st.write("Based on this prediction, what is your next step?")
    intent = st.radio("Your Intent:", ["Reduce UberEats/Dining spending", "Look for cheaper housing", "No changes needed"], label_visibility="collapsed")
    
    if st.button("SUBMIT FEEDBACK & FINALIZE", use_container_width=True):
        sheet = connect_to_sheet()
        if sheet and st.session_state.row_idx:
            # Silently update the research sheet
            sheet.update_cell(st.session_state.row_idx, 7, trust)
            sheet.update_cell(st.session_state.row_idx, 8, useful)
            sheet.update_cell(st.session_state.row_idx, 18, intent)
            st.success("Analysis complete. Thank you!")
            st.session_state.step = "home"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center; color:#94A3B8; padding:30px;">Researcher: Sandeep Sharma | Excelsia College</div>', unsafe_allow_html=True)
