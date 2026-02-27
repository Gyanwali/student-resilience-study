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
        "exp_breakdown": exp_vals
    }

# --- 3. UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .metric-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); 
                   padding: 20px; border-radius: 15px; text-align: center; }
    .ai-bubble { background: rgba(37, 99, 235, 0.08); border-left: 5px solid #2563EB; padding: 20px; 
                 border-radius: 12px; margin: 20px 0; line-height: 1.6; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; background: #2563EB !important; 
                       color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "finished":
    st.balloons()
    st.title("✅ Research Data Secured")
    st.markdown(f'<div class="ai-bubble">Thank you. ID: <b>{st.session_state.get("last_id")}</b> has been stored. You can now close this window.</div>', unsafe_allow_html=True)
    st.stop()

if st.session_state.step == "home":
    st.title("🛡️ Resilience Lab AI")
    st.info("Sydney Student Financial Research Project")
    if st.checkbox("I consent to participate in this study."):
        if st.button("INITIALIZE AI"):
            st.session_state.participant_id = f"RES-{random.randint(100000, 999999)}"
            st.session_state.step = "inputs"
            st.rerun()

elif st.session_state.step == "inputs":
    st.subheader(f"📍 ID: {st.session_state.participant_id}")
    with st.form("input_form"):
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield", "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
        addr = st.selectbox("Suburb", suburbs)
        custom_sub = st.text_input("If 'Other', specify:")
        final_addr = custom_sub if addr == "Other" else addr
        
        inc = st.number_input("Income ($/mo)", 500, 10000, 3200)
        rent = st.number_input("Rent ($/wk)", 100, 1500, 450)
        uber = st.slider("Uber/Lifestyle ($/wk)", 0, 800, 120)
        
        with st.expander("More Data Points"):
            lit = st.select_slider("Literacy", options=["Novice", "Intermediate", "Advanced"], value="Intermediate")
            p_supp = st.radio("Family Support?", ["No", "Yes"])
            p_amt = st.number_input("Support Amt ($/mo)", 0, 5000, 0)
            savings = st.number_input("Total Savings ($)", 0, 50000, 2000)
            groc = st.number_input("Groceries ($/wk)", 0, 500, 140)
            trans = st.number_input("Transport ($/wk)", 0, 300, 45)
            bills = st.number_input("Utilities ($/mo)", 0, 800, 150)
            remit = st.number_input("Remittance ($/mo)", 0, 3000, 0)
            months = st.number_input("Months in Sydney", 1, 120, 12)
            meals = st.radio("Skipped meals?", ["No", "Yes"])

     if st.form_submit_button("GENERATE REPORT"):
         data = {
                "income": inc, "p_supp": p_supp, "p_amt": p_amt, 
                "remit": remit, "rent": rent, "uber": uber, 
                "groc": groc, "trans": trans, "bills": bills, 
                "meals": meals, "addr": final_addr, 
                "savings": savings, "lit": lit, "months": months
            }
            
            st.session_state.data = data
            sheet = connect_to_sheet()
            if sheet:
                res = run_research_model(data)
                sydney_time = datetime.utcnow() + timedelta(hours=11)
                row = [
                    sydney_time.strftime("%Y-%m-%d %H:%M"), 
                    st.session_state.participant_id, 
                    rent, inc, final_addr, uber, 
                    "Pending", "Pending", res['score'], 
                    meals, p_supp, remit, p_amt, 
                    savings, trans, lit, months, "Pending"
                ]
                
                # --- DATA INTEGRITY FIX ---
                sheet.append_row(row)
                # Capture exact row number for this session to prevent overwriting
                st.session_state.target_row = len(sheet.get_all_values())
                
                st.session_state.step = "results"
                st.rerun()

elif st.session_state.step == "results":
    ai = run_research_model(st.session_state.data)
    st.title("📊 Resilience Dashboard")
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h3>{ai["score"]}</h3>Resilience</div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><h3>{ai["runway"]}</h3>Runway Mo.</div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><h3>{ai["prob"]}%</h3>Success</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="ai-bubble">
    <b>Diagnosis:</b> Housing in <b>{st.session_state.data['addr']}</b> takes <b>{ai['rent_pct']}%</b> of income.
    Your survival runway is <b>{ai['runway']} months</b>. 
    Reducing lifestyle spending is your primary leverage for resilience.
    </div>
    """, unsafe_allow_html=True)

    st.plotly_chart(px.pie(values=list(ai['exp_breakdown'].values()), names=list(ai['exp_breakdown'].keys()), hole=0.5), use_container_width=True)

    with st.form("feedback_form"):
        trust = st.select_slider("Trust AI logic?", options=["Low", "Neutral", "High"])
        useful = st.select_slider("Enlightening?", options=["No", "Neutral", "Yes"])
        intent = st.radio("Next Action:", ["Reduce spending", "Search housing", "No change"])
        
        if st.form_submit_button("SUBMIT & LOCK"):
            sheet = connect_to_sheet()
            if sheet:
                success = False
                # RETRY LOGIC: Try 3 times to find the row
                for _ in range(3):
                    try:
                        time.sleep(1.5) 
                        cell = sheet.find(st.session_state.participant_id)
                        sheet.update_cell(cell.row, 7, trust)
                        sheet.update_cell(cell.row, 8, useful)
                        sheet.update_cell(cell.row, 18, intent)
                        success = True
                        break
                    except:
                        continue
                
                # FALLBACK: If find fails, append feedback as a linked entry
                if not success:
                    sydney_time = datetime.utcnow() + timedelta(hours=11)
                    backup = [sydney_time.strftime("%Y-%m-%d %H:%M"), st.session_state.participant_id, "FALLBACK", "", "", "", trust, useful, "", "", "", "", "", "", "", "", "", intent]
                    sheet.append_row(backup)
                
                st.session_state.last_id = st.session_state.participant_id
                st.session_state.step = "finished"
                st.rerun()



