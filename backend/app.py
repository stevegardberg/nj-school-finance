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
df_map = pd.DataFrame(fetch("legislative_mapping"))
df_types = pd.DataFrame(fetch("vw_district_cohorts"))

# KEY NORMALIZATION
for df in [df_summary, df_map, df_types]:
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6).str[:6]

# CREATE LOOKUPS (This ensures filters have data)
leg_dict = dict(zip(df_map["cds_code"], df_map["legislative_district"]))
type_dict = dict(zip(df_types["cds_code"], df_types["district_type"]))
# Auto-detect name column
name_col = [c for c in df_types.columns if "name" in c.lower()][0]
name_dict = dict(zip(df_types["cds_code"], df_types[name_col]))

# APPLY MAPPINGS
df_summary["assigned_ld"] = df_summary["cds_code"].map(leg_dict).fillna("Unassigned")
df_summary["assigned_type"] = df_summary["cds_code"].map(type_dict).fillna("Unassigned")
df_summary["district_name"] = df_summary["cds_code"].map(name_dict).fillna("Unknown District")

# 3. FILTERS (Restored)
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
f1, f2, f3, f4 = st.columns(4)

with f1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All"] + sorted(df_summary["assigned_ld"].unique().tolist()))
with f2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All"] + sorted(df_summary["assigned_type"].unique().tolist()))

# Cascading Logic
df_cascade = df_summary.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

with f4: sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select..."] + sorted(df_cascade["district_name"].unique().tolist()))

# 4. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return Matrix"])
with tab1:
    if sel_dist != "Select...":
        st.dataframe(df_cascade[df_cascade["district_name"] == sel_dist], use_container_width=True)
    else:
        st.info("Select a district.")