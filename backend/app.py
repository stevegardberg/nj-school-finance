import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

# 1. DATABASE HANDSHAKE
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
    SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
    BASE_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(endpoint):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=10000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. LOAD DATA
raw_summary = fetch("state_aid_summary")
raw_types = fetch("vw_district_cohorts")

df_all = pd.DataFrame(raw_summary)
df_types = pd.DataFrame(raw_types)

# 3. STANDARDIZE JOIN KEYS
for df in [df_all, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

# 4. JOIN (USE OUTER TO KEEP ALL DISTRICTS)
df_joined = pd.merge(df_all, df_types, on="cds_code", how="outer")

# 5. CONSOLIDATE NAMES (Fixing the x/y issue)
# Prioritize metadata name, fallback to summary name, fallback to 'Unknown'
name_cols = [c for c in df_joined.columns if "district_name" in c]
df_joined["display_name"] = df_joined[name_cols].bfill(axis=1).iloc[:, 0].fillna("Unknown District")

# 6. METRICS
for col in ["actual_net_payout", "actual_tax_levy", "equalized_valuation"]:
    if col in df_joined.columns:
        df_joined[col] = pd.to_numeric(df_joined[col], errors='coerce').fillna(0)

# 7. UI
st.title("🏛️ NJ School Finance Intelligence")
# Ensure the dropdown list is sorted and contains every unique district from both tables
districts = sorted(df_joined["display_name"].unique().tolist())
sel_dist = st.selectbox("Select District:", ["Select..."] + districts)

if sel_dist != "Select...":
    st.markdown(f"#### 📍 Ledger for {sel_dist}")
    st.dataframe(df_joined[df_joined["display_name"] == sel_dist], use_container_width=True)
else:
    st.info("Select a district to view calculations.")