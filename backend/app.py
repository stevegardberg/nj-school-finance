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

# 2. LOAD & MERGE (Strictly on cds_code)
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    
    # Standardize CDS codes across tables
    for df in [df_sum, df_map]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
            
    # CDS-Only Join
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'district_name']], on='cds_code', how='left')
    
    # Handle missing names
    if 'district_name_y' in df.columns:
        df['district_name'] = df['district_name_y'].fillna(df['district_name_x'])
    
    return df

# 3. UI
df_merged = get_data()

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": 
    df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]

# Force dropdown to use unique values from state_aid_summary via cds_code match
sel_district = st.sidebar.selectbox("2️⃣ Select District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

page = st.sidebar.radio("Navigation", ["Financial Ledger", "Revenue Matrix"])

if sel_district != "Select...":
    if page == "Financial Ledger":
        st.title(f"📍 Ledger: {sel_district}")
        st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)
    elif page == "Revenue Matrix":
        target_cds = df_f[df_f['district_name'] == sel_district]['cds_code'].iloc[0]
        st.write(f"Querying revenue for CDS: {target_cds}")
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            st.dataframe(rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum'), use_container_width=True)
        else:
            st.info("No revenue data found for this CDS.")