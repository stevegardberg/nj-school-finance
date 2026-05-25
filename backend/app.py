import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

# 1. DATABASE HANDSHAKE
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
    BASE_URL = f"https://{st.secrets['project_id']}.supabase.co/rest/v1"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(endpoint):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=10000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA PIPELINE
raw_summary, raw_types = fetch("state_aid_summary"), fetch("vw_district_cohorts")
df_all = pd.DataFrame(raw_summary)
df_types = pd.DataFrame(raw_types)

for df in [df_all, df_types]:
    if "cds_code" in df.columns: df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

df_joined = pd.merge(df_all, df_types, on="cds_code", how="outer")
name_cols = [c for c in df_joined.columns if "district_name" in c]
df_joined["display_name"] = df_joined[name_cols].bfill(axis=1).iloc[:, 0].fillna("Unknown District")

# 3. FORMATTING ENGINE
def clean_html_currency_formatter(df):
    return df.to_html(index=False, escape=False)

# 4. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
f_col1, f_col2, f_col3 = st.columns(3)
with f_col1: sel_dist = st.selectbox("Target District:", ["Select..."] + sorted(df_joined["display_name"].unique().tolist()))

# 5. TABS & MATRICES
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_dist != "Select...":
        df_view = df_joined[df_joined["display_name"] == sel_dist].sort_values("fiscal_year")
        st.markdown(f"#### 📍 Ledger for {sel_dist}")
        st.write(clean_html_currency_formatter(df_view), unsafe_allow_html=True)
    else:
        st.info("Select a district to begin analysis.")

with tab2: st.markdown("#### UFB Appropriations Component Ledger")
with tab3: st.markdown("#### Return on Academic Investment Insights")