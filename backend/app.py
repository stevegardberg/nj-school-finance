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
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=5000", headers=headers, timeout=12)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. LOAD & CLEAN DATA
raw_summary = fetch("state_aid_summary")
raw_types = fetch("vw_district_cohorts")

df_all = pd.DataFrame(raw_summary)
df_types = pd.DataFrame(raw_types)

# Standardize join keys
for col in ["cds_code"]:
    if col in df_all.columns: df_all[col] = df_all[col].astype(str).str.strip().str.zfill(6)
    if col in df_types.columns: df_types[col] = df_types[col].astype(str).str.strip().str.zfill(6)

# 3. JOIN & CLEAN COLLISION
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# Use 'district_name_y' (from metadata) as the primary name
if "district_name_y" in df_joined.columns:
    df_joined["display_name"] = df_joined["district_name_y"].fillna("Unknown District")
elif "district_name_x" in df_joined.columns:
    df_joined["display_name"] = df_joined["district_name_x"].fillna("Unknown District")
else:
    df_joined["display_name"] = "Unknown District"

# 4. METRICS
for col in ["actual_net_payout", "actual_tax_levy", "equalized_valuation"]:
    df_joined[col] = pd.to_numeric(df_joined.get(col, 0), errors='coerce').fillna(0)

# 5. UI
st.title("🏛️ NJ School Finance Intelligence")
districts = sorted(df_joined["display_name"].unique().tolist())
sel_dist = st.selectbox("Select District:", ["Select..."] + districts)

if sel_dist != "Select...":
    st.dataframe(df_joined[df_joined["display_name"] == sel_dist])
else:
    st.info("Select a district.")