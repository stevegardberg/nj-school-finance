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
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")

    # Standardize and Debug
    for df in [df_sum, df_map, df_meta]:
        col = 'cds' if 'cds' in df.columns else 'cds_code'
        if col in df.columns:
            df.rename(columns={col: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Perform Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    
    # DYNAMIC MERGE: Only use columns that exist in the loaded dataframe
    available_cols = [c for c in ['cds_code', 'district_type'] if c in df_meta.columns]
    if len(available_cols) >= 1:
        df = df.merge(df_meta[available_cols], on='cds_code', how='left')
    else:
        st.sidebar.error(f"Metadata columns missing. Found: {list(df_meta.columns)}")
        df['district_type'] = 'Unknown'
    
    df['district_name'] = df['district_name'].fillna('Unknown')
    df['county_name'] = df['county_name'].fillna('Unassigned')
    return df

def add_metrics(df):
    numeric_cols = ['actual_state_aid', 'actual_tax_levy', 'equalized_valuation']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'actual_state_aid', 'actual_tax_levy', 'equalized_valuation']
    return df[[c for c in col_order if c in df.columns]]

# UI Execution
df_merged = add_metrics(get_data())

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("2️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna('Unassigned').unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("3️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().astype(str).tolist()))

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    st.dataframe(get_formatted_matrix(target_data), use_container_width=True)