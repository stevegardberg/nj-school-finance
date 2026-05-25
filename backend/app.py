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
    if "cds_code" in df.columns: df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6).str[:6]

# DYNAMIC NAME MAPPING (Finds the name column automatically)
name_col = [c for c in df_types.columns if "name" in c.lower()][0]
df_types = df_types.rename(columns={name_col: "district_name"})

# MERGE
df_all = pd.merge(df_summary, df_types, on="cds_code", how="left")
df_all["district_name"] = df_all["district_name"].fillna("Unknown District")

# Re-inject your original filter columns
df_all["assigned_ld"] = "District " + df_all.get("legislative_district", "Unassigned").astype(str)
df_all["assigned_type"] = df_all.get("district_type", "Unassigned")
df_all["assigned_county"] = df_all["cds_code"].str[:2] # Assuming prefix

# 3. CASCADING FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
f1, f2, f3, f4 = st.columns(4)

with f1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All"] + sorted(df_all["assigned_ld"].unique().tolist()))
with f2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All"] + sorted(df_all["assigned_type"].unique().tolist()))

df_cascade = df_all.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

with f4: sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select..."] + sorted(df_cascade["district_name"].unique().tolist()))

# 4. TABS & MATRIX
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return Matrix"])
with tab1:
    if sel_dist != "Select...":
        df_render = df_cascade[df_cascade["district_name"] == sel_dist]
        st.dataframe(df_render, use_container_width=True)
    else:
        st.info("Select a district to begin.")