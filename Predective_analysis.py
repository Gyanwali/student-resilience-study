import streamlit as st
import gspread
import math
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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

# --- 2. PREDICTIVE AI ENGINE (XAI LOGIC) ---
def run_research_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    # 4.33 weeks per month calculation
    exp_vals = {
        "Rent": float(data['rent']) * 4.33,
        "Groceries": float(data['groc']) * 4.33,
        "UberEats": float(data['uber']) * 4.33,
        "Transport": float(data['trans']) * 4.33,
        "Fixed Bills": float(data['bills']),
        "Remittance": float(data['remit'])
    }
    m_exp = sum(exp_vals.values())
    surplus = m_inc - m_exp
    
    # Success Probability (Sigmoid)
    z = (surplus / (m_exp if m_exp > 0 else 1)) * 5 
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus/500)), 1)

    # Resilience Indexing
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes": score -= 25
    
    return {
        "m_surplus": round(surplus, 2), 
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "uber_pct": round((exp_vals["UberEats"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Rent"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. UI STYLE & THEME ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .nav-header { background: #0F172A; padding: 25px; text-align: center; border-radius: 0 0 15px 15px; color: white; margin-bottom: 20px;}
    .res-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stMetric { background: #F1F5F9; padding: 10px; border-radius: 8px; border-left: 4px solid #2563EB; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

st.markdown('<div class="nav-header"><h1 style="color:white !important; font-size: 1.8rem;">Resilience Intelligence Lab</h1><p style="color:#38BDF8 !important;">XAI Diagnostic Terminal</p></div>', unsafe_allow_html=True)

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "home":
    st.markdown('<div class="res-card"><h3>Research Briefing</h3><p>This AI evaluates your financial shock-absorption. Data is anonymized for the Sydney Student Study.</p></div>', unsafe_allow_html=True)
    if st.button("INITIALIZE TERMINAL", use_container_width=True):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    with st.form("research_inputs"):
        st.markdown("### 📍 Context & Cashflow")
        addr = st.text_input("Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        inc = st.number_input("Monthly Income ($)", value=3200)
        p_supp = st.radio("Family Support?", ["No", "Yes"])
        p_amt = st.number_input("Monthly Support ($)", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Current Savings ($)", value=2000)
        
        st.markdown("### 📉 Behavioral Spending (Weekly)")
        rent = st.number_input("Weekly Rent ($)", value=450)
        uber = st.number_input("Weekly UberEats ($)", value=120)
        groc = st.number_input("Weekly Groceries ($)", value=140)
        trans = st.number_input("Weekly Transport ($)", value=45)
        bills = st.number_input("Monthly Bills ($)", value=150)
        remit = st.number_input("Monthly Remittance ($)", value=0)
        months = st.number_input("Months in Sydney", value=12)
        meals = st.radio("Skipped meals?", ["No", "Yes"])

        if st.form_submit_button("GENERATE DASHBOARD & SYNC"):
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                row = [datetime.now().strftime("%Y-%m-%d"), rent, inc, addr, uber, res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, res['prob']]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.markdown('<div class="res-card"><h3>📊 Resilience Intelligence Dashboard</h3>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Resilience Score", f"{ai['score']}/100")
    c2.metric("Success Prob.", f"{ai['prob']}%")
    c3.metric("Monthly Surplus", f"${ai['m_surplus']}")
    st.markdown('</div>', unsafe_allow_html=True)

    # VISUAL 1: SPENDING PIE CHART
    st.markdown('<div class="res-card"><h4>Spending Distribution</h4>', unsafe_allow_html=True)
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # VISUAL 2: XAI REASONING GAUGE
    st.markdown('<div class="res-card"><h4>AI Behavioral Reasoning (XAI)</h4>', unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = ai['score'],
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#2563EB"}, 'steps': [{'range': [0, 50], 'color': "#fee2e2"}, {'range': [50, 75], 'color': "#fef9c3"}, {'range': [75, 100], 'color': "#dcfce7"}]}
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    st.write(f"• **Housing Load:** {ai['rent_pct']}% of income.")
    st.write(f"• **Discretionary Leak:** UberEats is {ai['uber_pct']}% of your budget.")
    st.info(f"💡 Reducing UberEats by $30/week improves your success probability to {min(ai['prob']+12, 100.0)}%.")
    st.markdown('</div>', unsafe_allow_html=True)

    # BEHAVIORAL CHANGE INTERVENTION
    st.markdown('<div class="res-card" style="border: 2px solid #2563EB;"><h4>Behavioral Intent</h4>', unsafe_allow_html=True)
    st.write("Will you adjust your behavior based on this AI feedback?")
    pivot = st.radio("Action Plan:", ["Reduce Discretionary Spending", "Seek Cheaper Housing", "Maintain Current Lifestyle"])
    if st.button("SUBMIT INTENT & FINALIZE"):
        st.success("Impact recorded. Thank you for participating.")
        st.session_state.step = "home"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center; color:#94A3B8; padding:20px;">Researcher: Sandeep Sharma | Excelsia College</div>', unsafe_allow_html=True)
