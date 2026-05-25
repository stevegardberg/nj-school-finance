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
except Exception as e:
    st.error(f"Secret configuration error: {e}")
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

# 3. STANDARDIZE JOIN KEYS
# Ensure columns exist before processing
if "cds_code" in df_all.columns: 
    df_all["cds_code"] = df_all["cds_code"].astype(str).str.strip().str.zfill(6)
if "cds_code" in df_types.columns: 
    df_types["cds_code"] = df_types["cds_code"].astype(str).str.strip().str.zfill(6)

# 4. JOIN
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# 5. DEBUGGING: Print columns to help you see what happened
with st.sidebar:
    st.write("Columns found in data:", df_joined.columns.tolist())

# 6. FORCE-CREATE COLUMNS (Prevents KeyError)
if "district_name" not in df_joined.columns:
    df_joined["district_name"] = "Unknown District"
df_joined["district_name"] = df_joined["district_name"].fillna("Unknown District")

# 7. METRICS
df_joined["actual_net_payout"] = pd.to_numeric(df_joined.get("actual_net_payout", 0), errors='coerce').fillna(0)
df_joined["actual_tax_levy"] = pd.to_numeric(df_joined.get("actual_tax_levy", 0), errors='coerce').fillna(0)
df_joined["equalized_valuation"] = pd.to_numeric(df_joined.get("equalized_valuation", 0), errors='coerce').fillna(0)

# 8. UI
st.title("NJ School Finance Intelligence")
districts = sorted(df_joined["district_name"].unique().tolist())
sel_dist = st.selectbox("Select District:", ["Select..."] + districts)

if sel_dist != "Select...":
    st.dataframe(df_joined[df_joined["district_name"] == sel_dist])
else:
    st.info("Select a district.")