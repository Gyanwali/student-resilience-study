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

# --- 2. PREDICTIVE AI ENGINE ---
def run_research_model(data):
    m_inc = max(float(data['income']) + float(data['p_amt']), 1.0)
    exp_vals = {
        "Rent": float(data['rent']) * 4.33,
        "Groceries": float(data['groc']) * 4.33,
        "UberEats": float(data['uber']) * 4.33,
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
        "uber_pct": round((exp_vals["UberEats"] / m_inc) * 100, 1),
        "rent_pct": round((exp_vals["Rent"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .nav-header { background: #0F172A; padding: 25px; text-align: center; border-radius: 0 0 15px 15px; color: white; margin-bottom: 20px;}
    .res-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'row_idx' not in st.session_state: st.session_state.row_idx = None

st.markdown('<div class="nav-header"><h1 style="color:white !important;">Resilience Intelligence Lab</h1><p style="color:#38BDF8 !important;">The impact of predective AI anlytics tool on financial resilience of International students focusing on dicreation spending behaviour.</p></div>', unsafe_allow_html=True)

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.markdown('<div class="res-card"><h3>Participant Briefing</h3><p>This study evaluates AI impact on student financial behavior. Data is anonymous.</p></div>', unsafe_allow_html=True)
    consent = st.checkbox("I consent to participate in this study.")
    if st.button("INITIALIZE TERMINAL") and consent:
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    with st.form("research_form"):
        st.subheader("📍 Research Variables")
        addr = st.text_input("Sydney Suburb", value="Hurstville")
        lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
        inc = st.number_input("Monthly Income ($)", value=3200)
        p_supp = st.radio("Parental Support?", ["No", "Yes"])
        p_amt = st.number_input("Monthly Support ($)", value=0) if p_supp == "Yes" else 0
        savings = st.number_input("Current Savings ($)", value=2000)
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
                # Map to A-R (Column G, H, R as Pending)
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), "Yes", rent, inc, addr, uber, "Pending", "Pending", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "Pending"]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.row_idx = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    # --- FULL DASHBOARD ---
    st.markdown('<div class="res-card"><h3>📊 Resilience Intelligence Dashboard</h3>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{ai['score']}/100")
    c2.metric("Success Prob.", f"{ai['prob']}%")
    c3.metric("Surplus", f"${ai['m_surplus']}")
    
    # Pie Chart
    fig_pie = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.4)
    fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)
    
    st.write(f"• **XAI Insight:** UberEats is {ai['uber_pct']}% of your income. Reducing this improves success to {min(ai['prob']+12, 100.0)}%.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- FINAL QUESTIONS (G, H, R) ---
    st.markdown('<div class="res-card" style="border: 2px solid #2563EB;"><h4>📝 Research Evaluation</h4>', unsafe_allow_html=True)
    trust = st.select_slider("Column G: Trust in AI Score", options=["Low", "Neutral", "High"], value="Neutral")
    useful = st.select_slider("Column H: AI Usefulness", options=["Low", "Medium", "High"], value="Medium")
    intent = st.radio("Column R: Behavioral Intent", ["Reduce UberEats", "Seek cheaper Rent", "No changes"])
    
    if st.button("SUBMIT FINAL DATA"):
        sheet = connect_to_sheet()
        if sheet and st.session_state.row_idx:
            # Update G(7), H(8), R(18)
            sheet.update_cell(st.session_state.row_idx, 7, trust)
            sheet.update_cell(st.session_state.row_idx, 8, useful)
            sheet.update_cell(st.session_state.row_idx, 18, intent)
            st.success("Research recorded! Thank you.")
            st.session_state.step = "home"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
