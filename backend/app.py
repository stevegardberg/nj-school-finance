import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

# 1. HANDSHAKE
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
    BASE_URL = f"https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(endpoint):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=10000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA PIPELINE
df_all = pd.DataFrame(fetch("state_aid_summary"))
df_types = pd.DataFrame(fetch("vw_district_cohorts"))

for df in [df_all, df_types]:
    if "cds_code" in df.columns: df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

df_joined = pd.merge(df_all, df_types, on="cds_code", how="outer")
df_joined["display_name"] = df_joined["district_name_y"].fillna(df_joined["district_name_x"]).fillna("Unknown")

# 3. FORMATTER & RENAME MAP
rename_map = {
    "fiscal_year": "Fiscal Year",
    "adequacy_budget": "Adequacy Budget",
    "actual_net_payout": "Actual State Aid",
    "local_fair_share": "Local Fair Share",
    "actual_tax_levy": "Actual Tax Levy"
}
ordered_cols = ["fiscal_year", "adequacy_budget", "actual_net_payout", "local_fair_share", "actual_tax_levy"]

def clean_html_currency_formatter(df):
    df_clean = df.copy()
    for col in df_clean.columns:
        if col in ["adequacy_budget", "actual_net_payout", "local_fair_share", "actual_tax_levy"]:
            df_clean[col] = df_clean[col].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
    return df_clean.to_html(index=False, escape=False)

# 4. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
sel_dist = st.selectbox("Target District:", ["Select..."] + sorted(df_joined["display_name"].unique().tolist()))

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_dist != "Select...":
        df_view = df_joined[df_joined["display_name"] == sel_dist].sort_values("fiscal_year")
        # Ensure columns exist before filtering
        available_cols = [c for c in ordered_cols if c in df_view.columns]
        st.write(clean_html_currency_formatter(df_view[available_cols].rename(columns=rename_map)), unsafe_allow_html=True)
    else:
        st.info("Select a district to begin.")