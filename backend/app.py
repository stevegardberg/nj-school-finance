import streamlit as st
import pandas as pd
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
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=5000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA PIPELINE
df_summary = pd.DataFrame(fetch("state_aid_summary"))
df_types = pd.DataFrame(fetch("vw_district_cohorts"))

# CRITICAL: Clean both sides to ensure matching
for col in ["cds_code"]:
    if col in df_summary.columns: df_summary[col] = df_summary[col].astype(str).str.strip().str.zfill(6)
    if col in df_types.columns: df_types[col] = df_types[col].astype(str).str.strip().str.zfill(6)

# MERGE
df_all = pd.merge(df_summary, df_types, on="cds_code", how="left")

# FORCE COLUMN CREATION: This prevents the KeyError
if "district_name" not in df_all.columns:
    df_all["district_name"] = "Unknown District"
else:
    df_all["district_name"] = df_all["district_name"].fillna("Unknown District")

# 3. DEBUG: Check if we actually joined anything
with st.expander("🔍 Debug Join"):
    st.write(f"Summary rows: {len(df_summary)} | Joined rows: {len(df_all)}")
    st.write(f"Sample district names: {df_all['district_name'].unique()[:5]}")

# 4. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
districts = sorted(df_all["district_name"].dropna().unique().tolist())
sel_dist = st.selectbox("Select District:", ["Select..."] + districts)

if sel_dist != "Select...":
    st.dataframe(df_all[df_all["district_name"] == sel_dist])
else:
    st.info("Select a district.")