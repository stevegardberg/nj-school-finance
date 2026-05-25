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

# Standardize Keys
for df in [df_summary, df_types]:
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6).str[:6]

# Merge with Failsafe: Ensure columns exist even if empty
df_all = pd.merge(df_summary, df_types, on="cds_code", how="left")

# HARD INITIALIZE: Force required columns if missing
required_cols = ["district_name", "assigned_ld", "assigned_type", "assigned_county"]
for col in required_cols:
    if col not in df_all.columns:
        df_all[col] = "Unassigned"

# Fill NAs
df_all["district_name"] = df_all["district_name"].fillna("Unknown District")

# 3. FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
f1, f2, f3, f4 = st.columns(4)

with f1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All"] + sorted(df_all["assigned_ld"].dropna().unique().tolist()))
with f2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All"] + sorted(df_all["assigned_type"].dropna().unique().tolist()))
with f4: sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select..."] + sorted(df_all["district_name"].dropna().unique().tolist()))

# Cascading
df_cascade = df_all.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

# 4. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return Matrix"])
with tab1:
    if sel_dist != "Select...":
        st.dataframe(df_cascade[df_cascade["district_name"] == sel_dist], use_container_width=True)
    else:
        st.info("Select a district.")