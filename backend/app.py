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
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=5000", headers=headers, timeout=12)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. LOAD DATA
raw_summary = fetch("state_aid_summary")
raw_types = fetch("vw_district_cohorts")

df_all = pd.DataFrame(raw_summary)
df_types = pd.DataFrame(raw_types)

# 3. CRITICAL: STANDARDIZE JOIN KEYS
# Ensure both are strings, stripped of whitespace, and consistent length
for col in ["cds_code"]:
    if col in df_all.columns: df_all[col] = df_all[col].astype(str).str.strip().str.zfill(6)
    if col in df_types.columns: df_types[col] = df_types[col].astype(str).str.strip().str.zfill(6)

# 4. JOIN WITH FAILSAFE
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# FORCE CREATE COLUMNS IF MISSING
if "district_name" not in df_joined.columns:
    df_joined["district_name"] = "Unknown District"
df_joined["district_name"] = df_joined["district_name"].fillna("Unknown District")

# 5. METRICS
df_joined["actual_net_payout"] = pd.to_numeric(df_joined.get("actual_net_payout", 0), errors='coerce').fillna(0)
df_joined["actual_tax_levy"] = pd.to_numeric(df_joined.get("actual_tax_levy", 0), errors='coerce').fillna(0)
df_joined["equalized_valuation"] = pd.to_numeric(df_joined.get("equalized_valuation", 0), errors='coerce').fillna(0)

# 6. UI
sel_dist = st.selectbox("Select District:", ["Select..."] + sorted(df_joined["district_name"].unique().tolist()))

if sel_dist != "Select...":
    st.dataframe(df_joined[df_joined["district_name"] == sel_dist])
else:
    st.info("Select a district.")