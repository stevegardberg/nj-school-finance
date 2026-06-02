import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ School Finance Intelligence")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    res = requests.get(f"{BASE_URL}/{table}?limit=20000", headers=headers)
    return pd.DataFrame(res.json())

# 2. LOAD & MERGE
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_types = fetch_table("district_metadata_mapping") 

    for df in [df_sum, df_map, df_types]:
        target_col = 'cds' if 'cds' in df.columns else 'cds_code'
        if target_col in df.columns:
            df.rename(columns={target_col: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    
    # Merge Metadata (Defensive)
    if 'district_type' in df_types.columns:
        df = df.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')
    else:
        st.sidebar.error(f"Missing 'district_type'. Found: {list(df_types.columns)}")
        df['district_type'] = 'Unknown'
    
    if 'county_name' not in df.columns: df['county_name'] = 'Unassigned'
    return df

# Metrics
def add_metrics(df):
    potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                      'equalized_valuation', 'local_fair_share', 'district_income']
    for col in potential_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df = df.sort_values(['district_name', 'fiscal_year'])
    return df

def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 
                 'local_fair_share', 'actual_tax_levy', 'equalized_valuation']
    available_cols = [c for c in col_order if c in df.columns]
    return df[available_cols].copy()

# 3. APP EXECUTION
df_merged = add_metrics(get_data())

st.sidebar.header("Filter Settings")
# Safely handle dropdowns even if columns contain NaNs
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].fillna('Unknown').unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna('Unassigned').unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ Select District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

page = st.sidebar.radio("Navigation", ["Financial Ledger", "Comparative Analysis", "Revenue Matrix"])

if page == "Financial Ledger" and sel_district != "Select...":
    st.dataframe(get_formatted_matrix(df_f[df_f['district_name'] == sel_district]), use_container_width=True)
elif page == "Revenue Matrix" and sel_district != "Select...":
    target_cds = df_f[df_f['district_name'] == sel_district]['cds_code'].iloc[0]
    rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
    if not rev_data.empty:
        st.dataframe(rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum'), use_container_width=True)