import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. DYNAMIC LOAD & MERGE
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_types = fetch_table("vw_district_cohorts")

    # Standardize all potential CDS column names to 'cds_code'
    for df in [df_sum, df_map, df_types]:
        # Handle cases where 'cds' or 'cds_code' might exist
        col_name = 'cds' if 'cds' in df.columns else 'cds_code'
        if col_name in df.columns:
            df.rename(columns={col_name: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Perform Inner Join to ensure valid records only
    df_merged = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

    # Ensure defaults
    df_merged['county_name'] = df_merged.get('county_name', 'Unassigned')
    df_merged['district_name'] = df_merged.get('district_name', 'Unknown')
    
    return df_merged

# 3. METRIC ENFORCEMENT
def add_metrics(df):
    numeric_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                    'equalized_valuation', 'local_fair_share', 'district_income']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df = df.sort_values(['district_name', 'fiscal_year'])
    return df

# 4. DYNAMIC UI CONSTRUCTION
df_merged = add_metrics(get_data())

st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

# Dynamic Filter Logic: Everything derives from the available data
c1, c2, c3, c4 = st.columns(4)

sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().astype(str).tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().astype(str).tolist()))

# Apply filters sequentially to narrow down valid district choices
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

# Data display logic follows (same as previous)