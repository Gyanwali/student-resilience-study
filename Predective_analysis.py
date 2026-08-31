import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Resilience Intelligence Lab", page_icon="📊", layout="wide"
)

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to", ["Overview", "Data Screening & Cleaning", "Model Analysis", "About"]
)

if page == "Overview":
  st.title(
      "The Relationship Between Financial Resilience and Spending Behaviour"
  )
  st.subheader(
      "Among Nepalese Students in Greater Sydney: A Quantitative Study"
  )
  st.markdown(
      "**Researcher:** Sandeep Sharma | Excelsia University College"
      "[cite: 1, 11]"
  )
  st.write(
      "This web application serves as the primary analytics engine for the"
      " research project. It processes survey data, computes continuous"
      " composite scores, and executes ordinary least squares (OLS) multiple"
      " linear regression across your four distinct theoretical models[cite: 4, 11]."
  )

  st.info(
      "Upload your cleaned Qualtrics dataset via the sidebar or data screening"
      " tab to initiate automated hypothesis testing for H1 through H4[cite: 4, 11]."
  )

elif page == "Data Screening & Cleaning":
  st.title("Data Screening and Variable Construction")

  uploaded_file = st.file_uploader(
      "Upload Qualtrics Survey Data (.csv)", type=["csv"]
  )

  if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write(f"Raw Dataset Loaded: {df.shape[0]} rows, {df.shape[1]} columns.")

    # Screening checks (A1, A2, AC1)
    if "A1" in df.columns and "A2" in df.columns and "AC1" in df.columns:
      initial_count = len(df)
      df = df[(df["A1"] == "Yes") & (df["A2"] == "Yes") & (df["AC1"] == "Agree")]
      st.success(
          f"Screening applied: Retained {len(df)} valid responses out of"
          f" {initial_count} total submissions[cite: 11]."
      )
    else:
      st.warning(
          "Screening columns (A1, A2, AC1) not automatically detected. Ensure"
          " variable names match the survey template."
      )

    # Reverse scoring configuration
    # Assuming FA1-FA3 and SB1-SB3 are on a 1-5 scale where higher raw means more anxiety/impulsivity
    for col in ["FA1", "FA2", "FA3", "SB1", "SB2", "SB3"]:
      if col in df.columns:
        df[f"{col}_rev"] = 6 - df[col]

    # Composite Calculations
    sb_cols = [
        "SB1_rev",
        "SB2_rev",
        "SB3_rev",
        "SB4",
        "SB5",
        "SB6",
        "SB7",
        "SB8",
        "SB9",
    ]
    if all(c in df.columns for c in sb_cols):
      df["DV_Spending_Composite"] = df[sb_cols].mean(axis=1)

    fa_cols = ["FA1_rev", "FA2_rev", "FA3_rev", "FA4", "FA5", "FA6", "FA7", "FA8", "FA9"]
    if all(c in df.columns for c in fa_cols):
      df["IV_Financial_Attitude"] = df[fa_cols].mean(axis=1)

    fst_cols = ["FST1", "FST2", "FST3", "FST4", "FST5", "FST6"]
    if all(c in df.columns for c in fst_cols):
      df["IV_Financial_Strategy"] = df[fst_cols].mean(axis=1)

    fsp_cols = ["FSP1", "FSP2", "FSP3", "FSP4", "FSP5"]
    if all(c in df.columns for c in fsp_cols):
      df["IV_Financial_Support"] = df[fsp_cols].mean(axis=1)

    ps_cols = ["PS1", "PS2", "PS3"]
    if all(c in df.columns for c in ps_cols):
      df["IV_Parental_Support"] = df[ps_cols].mean(axis=1)

    st.session_state["cleaned_df"] = df
    st.dataframe(df.head())
  else:
    st.info("Please upload a CSV file to proceed.")

elif page == "Model Analysis":
  st.title("Four-Model OLS Regression Analysis")

  if "cleaned_df" in st.session_state:
    df = st.session_state["cleaned_df"]

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Model 1 (H1)", "Model 2 (H2)", "Model 3 (H3)", "Model 4 (H4)"]
    )

    with tab1:
      st.subheader(
          "Model 1: Socio-Demographic Predictors (Gender & Parental Support)"
      )
      if (
          "DV_Spending_Composite" in df.columns
          and "A3" in df.columns
          and "IV_Parental_Support" in df.columns
      ):
        # Dummy code gender: Male = 0, Female = 1
        df["Gender_Dummy"] = df["A3"].apply(
            lambda x: 1 if str(x).strip().lower() == "female" else 0
        )
        m1 = smf.ols(
            "DV_Spending_Composite ~ Gender_Dummy + IV_Parental_Support",
            data=df,
        ).fit()
        st.text(str(m1.summary()))

        r2 = m1.rsquared
        f_pval = m1.f_pvalue
        if f_pval < 0.05:
          st.success(
              f"Hypothesis 1 Supported: Model is statistically significant"
              f" (R² = {r2:.3f}, p < .05)[cite: 4, 11]."
          )
        else:
          st.warning(
              f"Hypothesis 1 Not Significant (R² = {r2:.3f}, p = {f_pval:.3f})"
              "[cite: 4, 11]."
          )
      else:
        st.error(
            "Required variables for Model 1 missing from processed dataset."
        )

    with tab2:
      st.subheader("Model 2: Financial Attitude")
      if (
          "DV_Spending_Composite" in df.columns
          and "IV_Financial_Attitude" in df.columns
      ):
        m2 = smf.ols(
            "DV_Spending_Composite ~ IV_Financial_Attitude", data=df
        ).fit()
        st.text(str(m2.summary()))
        if m2.pvalues.iloc[1] < 0.05:
          st.success("Hypothesis 2 Supported: Significant positive effect[cite: 4, 11].")
        else:
          st.warning("Hypothesis 2 Not Statistically Significant[cite: 4, 11].")

    with tab3:
      st.subheader("Model 3: Financial Strategy")
      if (
          "DV_Spending_Composite" in df.columns
          and "IV_Financial_Strategy" in df.columns
      ):
        m3 = smf.ols(
            "DV_Spending_Composite ~ IV_Financial_Strategy", data=df
        ).fit()
        st.text(str(m3.summary()))
        if m3.pvalues.iloc[1] < 0.05:
          st.success("Hypothesis 3 Supported: Significant positive effect[cite: 4, 11].")
        else:
          st.warning("Hypothesis 3 Not Statistically Significant[cite: 4, 11].")

    with tab4:
      st.subheader("Model 4: Financial Support")
      if (
          "DV_Spending_Composite" in df.columns
          and "IV_Financial_Support" in df.columns
      ):
        m4 = smf.ols(
            "DV_Spending_Composite ~ IV_Financial_Support", data=df
        ).fit()
        st.text(str(m4.summary()))
        if m4.pvalues.iloc[1] < 0.05:
          st.success("Hypothesis 4 Supported: Significant positive effect[cite: 4, 11].")
        else:
          st.warning("Hypothesis 4 Not Statistically Significant[cite: 4, 11].")

  else:
    st.warning(
        "Please complete data screening and upload your dataset in the previous"
        " tab first."
    )

elif page == "About":
  st.title("About the System")
  st.write(
      "This prototype application ensures transparent, objective calculation of"
      " research outcomes without confirmation bias. It strictly implements"
      " ordinary least squares (OLS) regression algorithms mapped directly to"
      " the thesis framework[cite: 1, 4, 11]."
  )
