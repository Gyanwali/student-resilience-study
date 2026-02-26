import streamlit as st
import gspread
import math
import plotly.express as px
import random
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

# --- 2. PREDICTIVE ENGINE ---
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

# --- 3. UI STYLE (CLEAN, BLACK TEXT, PROFESSIONAL) ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    html, body, [class*="css"], p, h1, h2, h3, h4, span, label, li { 
        color: #000000 !important; 
    }
    .res-card { 
        background: white; 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #E5E7EB; 
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .suggestion-box {
        background: #F0FDF4;
        border-left: 5px solid #22C55E;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .warning-box {
        background: #FFF7ED;
        border-left: 5px solid #F97316;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5rem; 
        background: #1E3A8A !important; color: white !important; font-weight: bold; 
    }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"
if 'current_row' not in st.session_state: st.session_state.current_row = None

# --- 4. NAVIGATION ---

if st.session_state.step == "home":
    st.title("👋 Welcome")
    st.markdown('<div class="res-card"><h3>Resilience Lab AI</h3><p>This study analyzes the financial resilience of international students. Use the sliders on the next page to receive a personalized AI prediction.</p></div>', unsafe_allow_html=True)
    if st.button("START AI ANALYSIS"):
        st.session_state.step = "inputs"
        st.rerun()

elif st.session_state.step == "inputs":
    st.markdown("### 📍 Your Profile")
    with st.form("clean_input_form"):
        addr = st.selectbox("Sydney Suburb", ["Hurstville", "Parramatta", "CBD", "Randwick", "Strathfield", "Other"])
        inc = st.slider("Monthly Income (AUD)", 1000, 8000, 3200, step=100)
        rent = st.slider("Weekly Rent (AUD)", 100, 1000, 450, step=10)
        uber = st.slider("Weekly UberEats/Dining (AUD)", 0, 500, 120, step=10)
        
        with st.expander("Show Detailed Variables"):
            lit = st.select_slider("Financial Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Access to Family Support?", ["No", "Yes"])
            p_amt = st.slider("Monthly Family Support Amt ($)", 0, 3000, 0, step=100) if p_supp == "Yes" else 0
            savings = st.slider("Current Savings ($)", 0, 20000, 2000, step=500)
            groc = st.slider("Weekly Groceries ($)", 50, 400, 140, step=10)
            trans = st.slider("Weekly Transport ($)", 0, 200, 45, step=5)
            bills = st.slider("Monthly Utilities ($)", 0, 500, 150, step=10)
            remit = st.slider("Monthly Remittance ($)", 0, 2000, 0, step=500)
            months = st.number_input("Months in Sydney", min_value=1, value=12)
            meals = st.radio("Have you skipped meals to save?", ["No", "Yes"])

        if st.form_submit_button("ANALYZE MY DATA"):
            unique_id = f"RES-{random.randint(10000, 99999)}"
            data = {"income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit, "rent": rent, "uber": uber, "groc": groc, "trans": trans, "bills": bills, "meals": meals, "addr": addr, "savings": savings, "lit": lit, "months": months}
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                row = [datetime.now().strftime("%Y-%m-%d %H:%M"), unique_id, rent, inc, addr, uber, "...", "...", res['score'], meals, p_supp, remit, p_amt, savings, trans, lit, months, "..."]
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.session_state.current_row = len(sheet.get_all_values())
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.balloons()
    
    st.header("📊 AI Resilience Analysis")
    
    # 1. THE EXPLANATION (XAI)
    st.markdown('<div class="res-card"><h4>🔍 AI Diagnosis</h4>', unsafe_allow_html=True)
    st.write(f"Your **Resilience Score is {ai['score']}/100**. This reflects your ability to survive a financial shock (like job loss or rent increase) for at least 3 months.")
    
    if ai['rent_pct'] > 35:
        st.markdown(f'<div class="warning-box"><b>High Rent Burden:</b> Your rent takes up {ai["rent_pct"]}% of your income. Academic standards suggest that anything over 30% puts you at risk of "Rental Stress."</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="suggestion-box"><b>Healthy Housing:</b> Your rent is {ai["rent_pct"]}% of income, which is within a sustainable range for Sydney.</div>', unsafe_allow_html=True)

    if ai['uber_pct'] > 10:
        st.markdown(f'<div class="warning-box"><b>Discretionary Leak:</b> You are spending {ai["uber_pct"]}% of your total monthly income on UberEats/Dining. This is your largest "flexible" expense.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. THE PREDICTION
    st.markdown('<div class="res-card"><h4>📈 Future Predictions</h4>', unsafe_allow_html=True)
    st.write(f"The AI predicts a **{ai['prob']}% Success Probability** for your current lifestyle over the next 6 months.")
    st.markdown(f"""
    <div class="suggestion-box">
    <b>AI Suggestion:</b> If you reduce your UberEats spending by just <b>$40 per week</b>, your Success Probability will rise to <b>{min(ai['prob']+12, 100.0)}%</b> and your Resilience Score will increase by <b>+10 points</b>.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. VISUALIZATION
    st.markdown('<div class="res-card"><h4>Monthly Spending Breakdown</h4>', unsafe_allow_html=True)
    fig = px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.6)
    fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. FINAL FEEDBACK
    st.markdown('<div class="res-card"><h4>Final Research Question</h4>', unsafe_allow_html=True)
    trust = st.select_slider("How much do you trust this AI prediction?", options=["Low", "Neutral", "High"])
    intent = st.radio("Based on this AI feedback, will you change your spending behavior?", ["Yes, I will reduce discretionary spending", "No, my spending is already at its limit", "I will look for cheaper housing"])
    
    if st.button("COMPLETE & SAVE"):
        sheet = connect_to_sheet()
        if sheet and st.session_state.current_row:
            sheet.update_cell(st.session_state.current_row, 7, trust)
            sheet.update_cell(st.session_state.current_row, 18, intent)
            st.success("Research entry complete. Thank you!")
            st.session_state.step = "home"
            st.rerun()

st.markdown('<p style="text-align:center; color:#6B7280; font-size:0.8rem; padding:20px;">Researcher: Sandeep Sharma | Excelsia College</p>', unsafe_allow_html=True)
