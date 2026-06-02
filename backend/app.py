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
    
    for df in [df_sum, df_map]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Perform stable merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'district_name']], on='cds_code', how='left')
    df['district_name'] = df['district_name_y'].fillna(df['district_name_x'])
    df['county_name'] = df.get('county_name', 'Unassigned')
    return df

def add_metrics(df):
    numeric_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                    'equalized_valuation', 'local_fair_share', 'district_income']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df = df.sort_values(['district_name', 'fiscal_year'])
    return df

def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 
                 'local_fair_share', 'actual_tax_levy', 'equalized_valuation', 'district_income']
    df_out = df[[c for c in col_order if c in df.columns]].copy()
    return df_out

# Execution
df_merged = add_metrics(get_data())

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("2️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna('Unassigned').unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("3️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

# Page Content
st.title("🏛️ New Jersey School Finance Intelligence")
page = st.radio("Navigation", ["Financial Ledger", "Revenue Matrix"], horizontal=True)

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    if page == "Financial Ledger":
        st.subheader(f"📍 Ledger: {sel_district}")
        st.dataframe(get_formatted_matrix(target_data), use_container_width=True)
    else:
        target_cds = target_data['cds_code'].iloc[0]
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            st.dataframe(rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum'), use_container_width=True)
        else:
            st.info("No revenue data found.")