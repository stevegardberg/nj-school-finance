import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ School Finance Intelligence")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200: return pd.DataFrame()
        data = res.json()
        if not data: break
        all_records.extend(data)
        page += 1
    return pd.DataFrame(all_records)

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")
    
    if df_sum.empty: return pd.DataFrame()

    # Standardize CDS Codes
    for df in [df_sum, df_map, df_meta]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # 1. Base Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # 2. Schema-Aware Metadata Merge
    required_meta = ['cds_code', 'district_type', 'district_name']
    available_meta = [col for col in required_meta if col in df_meta.columns]
    
    if len(available_meta) > 1:
        df = df.merge(df_meta[available_meta], on='cds_code', how='left', suffixes=('', '_meta'))
    
    # 3. Guaranteed column initialization to prevent crashes
    for col, default in [('district_type', 'Unknown'), ('county_name', 'Unassigned'), 
                         ('ld_display', 'N/A'), ('district_name', 'Unknown District')]:
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)
            
    df['display_name'] = df['district_name'].astype(str) + " (" + df['county_name'].astype(str) + ")"
    return df

def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    numeric_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                    'equalized_valuation', 'local_fair_share', 'district_income']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def get_formatted_matrix(df):
    rename_map = {'fiscal_year': 'Fiscal Year', 'actual_state_aid': 'Actual Aid', 'actual_tax_levy': 'Actual Levy'}
    return df.rename(columns=rename_map)

# UI Execution
df_merged = add_metrics(get_data())

st.markdown("### 🏛️ NJ School Finance Intelligence")

if df_merged.empty:
    st.error("No data loaded. Check Supabase table status.")
else:
    c1, c2, c3, c4 = st.columns(4)
    
    # Filter options
    ld_opts = ["All"] + sorted([x for x in df_merged['ld_display'].unique() if x and x != 'N/A'])
    type_opts = ["All"] + sorted([x for x in df_merged['district_type'].unique() if x and x != 'Unknown'])
    county_opts = ["All"] + sorted([x for x in df_merged['county_name'].unique() if x and x != 'Unassigned'])

    sel_ld = c1.selectbox("1️⃣ Legislative:", ld_opts)
    sel_type = c2.selectbox("2️⃣ District Type:", type_opts)
    sel_county = c3.selectbox("3️⃣ County:", county_opts)

    # Filtered dataframe
    df_f = df_merged.copy()
    if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
    if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
    if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

    sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['display_name'].unique().tolist()))

    if sel_district != "Select...":
       target_data = df_f[df_f['display_name'] == sel_district]
       st.subheader(f"📍 Financial Ledger: {sel_district}")
       st.dataframe(get_formatted_matrix(target_data), use_container_width=True)

#