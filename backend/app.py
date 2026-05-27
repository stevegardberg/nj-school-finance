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

# Load full datasets
df_summary = fetch_paginated_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary")
df_map = fetch_paginated_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping")
df_types = fetch_paginated_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/district_metadata_mapping")

# 2. DATA PIPELINE
# Standardize keys
for df in [df_summary, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6).str[:6]

# Merge
df_merged = df_summary.merge(df_map[['cds_code', 'legislative_district']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# Cleanup & Formatting
df_merged["assigned_ld"] = df_merged["legislative_district"].apply(lambda x: f"District {int(x)}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged["district_type"].fillna("Unassigned")
# Calculate columns
df_merged['YoY_State_Aid_Diff'] = df_merged.groupby('district_name')['actual_state_aid'].diff().fillna(0)
df_merged['Tax_Levy_per_100'] = (df_merged['actual_tax_levy'].astype(float) / df_merged['equalized_valuation'].astype(float).replace(0, 1)) * 100

# 3. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset All"): st.rerun()

c1, c2, c3, c4 = st.columns(4)
# Legislative Filter
ld_options = sorted([ld for ld in df_merged["assigned_ld"].unique() if ld != "Unassigned"], key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + ld_options)

# Type Filter
type_options = sorted([t for t in df_merged["assigned_type"].unique() if t != "Unassigned"])
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + type_options)

# Filter logic
df_cascade = df_merged.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted([d for d in df_cascade["district_name"].unique() if isinstance(d, str)]))

# 4. MATRIX & PEER GROUP
if sel_district != "Select...":
    df_render = df_cascade[df_cascade['district_name'] == sel_district].sort_values("fiscal_year")
    col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']
    
    st.markdown(f"#### 📍 Ledger: {sel_district}")
    st.dataframe(df_render[col_order], use_container_width=True)
    
    st.markdown("#### 📊 District Type Peer Group")
    st.dataframe(df_types[df_types['district_name'] == sel_district], use_container_width=True)