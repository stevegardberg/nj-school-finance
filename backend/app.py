import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ School Finance Intelligence")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    # This robust fetch handles large datasets and ensures we get everything
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD & MERGE
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")

    # Standardize CDS_CODE to 6-digit string
    for df in [df_sum, df_map, df_meta]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    df = df.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')
    
    return df

# 3. METRICS & FORMATTING
def add_metrics(df):
    numeric_cols = ['actual_state_aid', 'actual_tax_levy', 'equalized_valuation']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'actual_state_aid', 'actual_tax_levy', 'equalized_valuation']
    return df[[c for c in col_order if c in df.columns]]

# 4. UI
df_merged = add_metrics(get_data())

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("2️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna('Unassigned').unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = st.sidebar.selectbox("3️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

page = st.sidebar.radio("Navigation", ["Financial Ledger", "Revenue Matrix"])

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    target_cds = target_data['cds_code'].iloc[0]

    if page == "Financial Ledger":
        st.subheader(f"📍 Ledger: {sel_district}")
        st.dataframe(get_formatted_matrix(target_data), use_container_width=True)
        
        # Comparative Averages
        st.markdown("---")
        val = target_data['ld_display'].iloc[0]
        st.subheader(f"🏛️ Legislative District Average: {val}")
        peers = df_merged[df_merged['ld_display'] == val].groupby('fiscal_year').mean(numeric_only=True).reset_index()
        st.dataframe(get_formatted_matrix(peers), use_container_width=True)

    elif page == "Revenue Matrix":
        st.subheader(f"🧮 Revenue Matrix: {sel_district}")
        # Explicit query using the confirmed cds_code column
        rev_url = f"revenue?cds_code=eq.{target_cds}"
        rev_data = fetch_table(rev_url)
        
        if not rev_data.empty:
            pivot = rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum')
            st.dataframe(pivot, use_container_width=True)
        else:
            st.info(f"No revenue records found for CDS {target_cds}. Ensure data exists for this specific ID.")