import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}

@st.cache_data(ttl=3600)
def fetch_paginated_data(url):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{url}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# Load data
df_summary = fetch_paginated_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary")
df_map = fetch_paginated_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping")
df_types = fetch_paginated_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/district_metadata_mapping")

# 2. CONTRACT-VERIFIED MERGE
# Initialize with empty shells to guarantee columns exist for the merge
df_merged = df_summary.copy()
if 'cds_code' not in df_merged.columns: df_merged['cds_code'] = None

# Helper to verify and merge
def safe_merge(df_left, df_right, left_on, right_on, cols_to_merge):
    # Only merge if right df has the required columns
    if all(col in df_right.columns for col in cols_to_merge):
        return df_left.merge(df_right[cols_to_merge], on=left_on, how='left')
    return df_left

# Execute merges only if data is valid
df_merged = safe_merge(df_merged, df_map, 'cds_code', 'cds_code', ['cds_code', 'legislative_district'])
df_merged = safe_merge(df_merged, df_types, 'cds_code', 'cds_code', ['cds_code', 'district_type'])

# 3. CLEANUP & FORMATTING
# Handle potential missing columns created by the safe_merge
if 'legislative_district' not in df_merged.columns: df_merged['legislative_district'] = None
if 'district_type' not in df_merged.columns: df_merged['district_type'] = "Unassigned"

df_merged["assigned_ld"] = df_merged["legislative_district"].apply(lambda x: f"District {int(x)}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged["district_type"].fillna("Unassigned")

# 4. UI & FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
c1, c2 = st.columns(2)
ld_options = sorted([ld for ld in df_merged["assigned_ld"].unique() if ld != "Unassigned"], key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + ld_options)
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged["assigned_type"].unique()))

# Cascade filtering
df_cascade = df_merged.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

st.dataframe(df_cascade)