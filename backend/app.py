import streamlit as st
import pandas as pd
import requests

st.set_page_config(layout="wide")

# 1. HANDSHAKE & CONFIG
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
    SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
    BASE_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(url):
    try:
        r = requests.get(f"{url}?limit=10000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA PIPELINE
df_all_summary = pd.DataFrame(fetch(f"{BASE_URL}/state_aid_summary"))
df_all_mapping = pd.DataFrame(fetch(f"{BASE_URL}/legislative_mapping"))
df_all_types = pd.DataFrame(fetch(f"{BASE_URL}/vw_district_cohorts"))

# Normalize keys
for df in [df_all_summary, df_all_mapping, df_all_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Merge Logic & Column Creation
leg_dict = dict(zip(df_all_mapping["cds_code"], df_all_mapping["legislative_district"]))
type_dict = dict(zip(df_all_types["cds_code"], df_all_types["district_type"]))
name_col = [c for c in df_all_types.columns if "name" in c.lower()][0]
name_dict = dict(zip(df_all_types["cds_code"], df_all_types[name_col]))

df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "Unassigned"))
df_all_summary["district_name"] = df_all_summary["cds_code"].map(lambda x: name_dict.get(x, "Unknown"))

# 3. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
f1, f2, f3, f4 = st.columns(4)

with f1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All"] + sorted(df_all_summary["assigned_ld"].unique().tolist()))
with f2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All"] + sorted(df_all_summary["assigned_type"].unique().tolist()))
with f4: sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select..."] + sorted(df_all_summary["district_name"].unique().tolist()))

# Cascading Filter Logic
df_cascade = df_all_summary.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

# 4. TABS & MATRIX
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_dist != "Select...":
        df_render = df_cascade[df_cascade["district_name"] == sel_dist]
        st.dataframe(df_render, use_container_width=True)
    else:
        st.info("Select a district.")