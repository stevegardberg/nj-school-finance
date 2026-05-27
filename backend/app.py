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

# 2. ROBUST DATA FETCHING
def fetch_and_validate(url, required_cols):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if not data: return pd.DataFrame(columns=required_cols)
        df = pd.DataFrame(data)
        # Ensure only columns we need are kept, or return empty if missing
        if all(col in df.columns for col in required_cols):
            return df[required_cols]
    return pd.DataFrame(columns=required_cols)

# Load data with strict column requirements
df_summary = fetch_and_validate(URLS["Summary"], ["cds_code", "fiscal_year", "district_name", "actual_state_aid", "adequacy_budget", "uncapped_aid", "equalized_valuation", "district_income", "local_fair_share", "actual_tax_levy", "s2_adjustment"])
df_mapping = fetch_and_validate(URLS["Mapping"], ["cds_code", "legislative_district"])
df_types = fetch_and_validate(URLS["Types"], ["cds_code", "district_type"])

# Clean IDs
for df in [df_summary, df_mapping, df_types]:
    if not df.empty:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6).str[:6]

# Merge logic (only if columns exist)
df_merged = df_summary.copy()
if not df_mapping.empty:
    df_merged = df_merged.merge(df_mapping, on="cds_code", how="left")
if not df_types.empty:
    df_merged = df_merged.merge(df_types, on="cds_code", how="left")

# Metadata Cleanup
df_merged["assigned_ld"] = df_merged.get("legislative_district", pd.Series([None]*len(df_merged))).apply(lambda x: f"District {x}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged.get("district_type", pd.Series(["Unassigned"]*len(df_merged)))

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
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 District Type Analysis", "🎯 Academic Return Matrix"])

with tab1:
    st.write("Validation Matrix")
with tab2:
    st.markdown("#### 📊 District Type Analysis")
    if not df_merged.empty and "district_type" in df_merged.columns:
        if sel_type != "All District Types":
            st.dataframe(df_merged[df_merged["assigned_type"] == sel_type])
        else:
            st.write("Please select a District Type to view data.")
    else:
        st.error("District Type data is currently unavailable in the database.")