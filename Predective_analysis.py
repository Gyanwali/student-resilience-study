import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import math
import plotly.express as px
import random
from datetime import datetime, timedelta

# --- 1. SECURE DATABASE INFRASTRUCTURE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Of3IskkddrEKLhG1P6QsitzaX6TMrN6czkaus2Tliwo"

# FIX 1: Explicitly define scopes so gspread has WRITE permission
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def connect_to_sheet():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
        # FIX 2: Use Credentials with explicit scopes instead of service_account_from_dict
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client.open_by_url(SHEET_URL).worksheet("Form Responses 1")
    except Exception as e:
        st.error(f"❌ Sheet connection failed: {e}")  # FIX 3: Surface the real error
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
    prob_success = round(1 / (1 + math.exp(-z)) * 100, 1) if surplus > 0 else round(max(5.0, 25.0 + (surplus / 500)), 1)
    
    lit_map = {"Novice": 30, "Intermediate": 65, "Advanced": 95}
    score = ((surplus / m_inc) * 40) + ((lit_map[data['lit']]) * 0.2) + (20 if data['p_supp'] == "Yes" else 0) + 30
    if data['meals'] == "Yes":
        score -= 25
    
    return {
        "m_surplus": round(surplus, 2),
        "score": int(min(max(score, 5), 100)),
        "prob": min(prob_success, 100.0),
        "runway": runway,
        "rent_pct": round((exp_vals["Housing (Rent)"] / m_inc) * 100, 1),
        "uber_pct": round((exp_vals["Lifestyle (Uber)"] / m_inc) * 100, 1),
        "exp_breakdown": exp_vals
    }

# --- 3. PREMIUM UI STYLE ---
st.set_page_config(page_title="Resilience Lab AI", layout="centered")
st.markdown("""
<style>
    .metric-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(128,128,128,0.2);
                   padding: 20px; border-radius: 15px; text-align: center; }
    .ai-bubble { background: rgba(37,99,235,0.08); border-left: 5px solid #2563EB; padding: 20px;
                 border-radius: 12px; margin: 20px 0; line-height: 1.6; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem;
                       background: #2563EB !important; color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state:
    st.session_state.step = "home"

# --- 4. NAVIGATION FLOW ---

if st.session_state.step == "finished":
    st.balloons()
    st.title("✅ Research Data Secured")
    st.markdown(f'<div class="ai-bubble">Thank you. ID: <b>{st.session_state.get("last_id")}</b> has been stored. You may now close this window.</div>', unsafe_allow_html=True)
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
        suburbs = sorted(["Hurstville", "Parramatta", "Sydney CBD", "Randwick", "Strathfield",
                           "Burwood", "Auburn", "Kensington", "Rhodes", "Wolli Creek", "Other"])
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
                "income": inc, "p_supp": p_supp, "p_amt": p_amt, "remit": remit,
                "rent": rent, "uber": uber, "groc": groc, "trans": trans,
                "bills": bills, "meals": meals, "addr": final_addr,
                "savings": savings, "lit": lit, "months": months
            }
            st.session_state.data = data
            res = run_research_model(data)
            st.session_state.res = res

            sheet = connect_to_sheet()
            if sheet:
                sydney_time = datetime.utcnow() + timedelta(hours=11)

                # FIX 4: Build the COMPLETE row upfront — no Pending placeholders
                # Column order: Timestamp, ID, Rent, Income, Suburb, Uber,
                #               Trust(placeholder), Useful(placeholder),
                #               Score, Meals, FamilySupport, Remittance,
                #               SupportAmt, Savings, Transport, Literacy, Months, Intent(placeholder)
                row = [
                    sydney_time.strftime("%Y-%m-%d %H:%M"),  # col 1
                    st.session_state.participant_id,          # col 2
                    rent,                                     # col 3
                    inc,                                      # col 4
                    final_addr,                               # col 5
                    uber,                                     # col 6
                    "",                                       # col 7: Trust (filled later)
                    "",                                       # col 8: Useful (filled later)
                    res['score'],                             # col 9
                    meals,                                    # col 10
                    p_supp,                                   # col 11
                    remit,                                    # col 12
                    p_amt,                                    # col 13
                    savings,                                  # col 14
                    trans,                                    # col 15
                    lit,                                      # col 16
                    months,                                   # col 17
                    ""                                        # col 18: Intent (filled later)
                ]

                try:
                    # FIX 5: Append row and immediately capture the TRUE row index
                    # from the API response — no second get_all_values() call needed
                    append_result = sheet.append_row(row, value_input_option="USER_ENTERED")
                    
                    # The updated range tells us exactly which row was written, e.g. "Form Responses 1!A42:R42"
                    updated_range = append_result.get("updates", {}).get("updatedRange", "")
                    if updated_range:
                        # Parse row number from range string like "Sheet1!A42:R42"
                        import re
                        row_numbers = re.findall(r'\d+', updated_range.split("!")[-1])
                        st.session_state.target_row = int(row_numbers[0]) if row_numbers else None
                    
                    st.session_state.step = "results"
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Failed to save data: {e}")
            else:
                st.error("❌ Could not connect to Google Sheets. Check your secrets configuration.")

elif st.session_state.step == "results":
    ai = st.session_state.res  # FIX 6: Reuse cached result, don't recalculate
    st.title("📊 Resilience Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.markdown(f'<div class="metric-card"><h3>{ai["score"]}</h3>Resilience</div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><h3>{ai["runway"]}</h3>Runway Mo.</div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><h3>{ai["prob"]}%</h3>Success</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="ai-bubble">
    <b>Analysis:</b> Your rent in <b>{st.session_state.data['addr']}</b> takes <b>{ai['rent_pct']}%</b> of income.<br>
    Your survival runway is <b>{ai['runway']} months</b>.
    </div>
    """, unsafe_allow_html=True)

    st.plotly_chart(
        px.pie(values=list(ai['exp_breakdown'].values()),
               names=list(ai['exp_breakdown'].keys()), hole=0.5),
        use_container_width=True
    )

    with st.form("feedback_form"):
        st.subheader("🎯 Final Evaluation")
        trust = st.select_slider("Trust AI logic?", options=["Low", "Neutral", "High"])
        useful = st.select_slider("Enlightening?", options=["No", "Neutral", "Yes"])
        intent = st.radio("Next Action:", ["Reduce spending", "Search housing", "No change"])

        if st.form_submit_button("SUBMIT & LOCK"):
            sheet = connect_to_sheet()
            if sheet and st.session_state.get('target_row'):
                try:
                    row_idx = st.session_state.target_row
                    # FIX 7: Batch update in one API call instead of 3 separate calls
                    sheet.update(f"G{row_idx}:H{row_idx}", [[trust, useful]])
                    sheet.update_cell(row_idx, 18, intent)

                    st.session_state.last_id = st.session_state.participant_id
                    st.session_state.step = "finished"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save feedback: {e}")
            else:
                st.error("❌ Session expired or row not found. Please restart.")
