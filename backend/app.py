import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(layout="wide")

# 1. SETUP
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
except Exception:
    st.error("🔒 Security credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "Summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "Mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "Types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
}

# 2. DATA FETCH & VALIDATION
def fetch_data(url):
    response = requests.get(url, headers=headers)
    return pd.DataFrame(response.json()) if response.status_code == 200 else pd.DataFrame()

df_summary = fetch_data(URLS["Summary"])
df_mapping = fetch_data(URLS["Mapping"])
df_types = fetch_data(URLS["Types"])

# Standardization
for df in [df_summary, df_mapping, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6).str[:6]

# Merge
df_merged = df_summary.merge(df_mapping[["cds_code", "legislative_district"]], on="cds_code", how="left")
df_merged = df_merged.merge(df_types[["cds_code", "district_type"]], on="cds_code", how="left")

# Metadata Cleanup
df_merged["assigned_ld"] = df_merged["legislative_district"].apply(lambda x: f"District {x}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged["district_type"].fillna("Unassigned")

# Sorting Helpers
def extract_num(s):
    nums = re.findall(r'\d+', str(s))
    return int(nums[0]) if nums else 0

master_ld_options = sorted([ld for ld in df_merged["assigned_ld"].unique() if ld != "Unassigned"], key=extract_num)
master_type_options = sorted([t for t in df_merged["assigned_type"].unique() if t != "Unassigned"])

# 3. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

c1, c2 = st.columns(2)
with c1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options)
with c2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options)

# 4. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 District Type Peer Group", "🎯 Academic Return Matrix"])

with tab1:
    st.write("Validation Matrix Content")
with tab2:
    st.markdown("#### 📊 District Type Analysis")
    if sel_type != "All District Types":
        st.dataframe(df_merged[df_merged["assigned_type"] == sel_type])
    else:
        st.write("Please select a District Type to view data.")