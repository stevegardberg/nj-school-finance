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
    # DIAGNOSTIC: Show the raw JSON if empty
    return pd.DataFrame(res.json())

# 2. LOAD & MERGE
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_types = fetch_table("district_metadata_mapping") 

    # DIAGNOSTIC: Force display of the raw data structure
    st.sidebar.write("Raw Metadata Data Preview:", df_types.head(2))

    for df in [df_sum, df_map, df_types]:
        target_col = 'cds' if 'cds' in df.columns else 'cds_code'
        if target_col in df.columns:
            df.rename(columns={target_col: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    df = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    
    # If df_types is empty, we must fallback or the app breaks
    if not df_types.empty and 'district_type' in df_types.columns:
        df = df.merge(df_types[['cds_code', 'district_name', 'district_type']], on='cds_code', how='left')
    else:
        df['district_type'] = 'N/A'
        df['district_name'] = df['district_name'] if 'district_name' in df.columns else 'Unknown'
    
    return df

# 3. METRICS
def add_metrics(df):
    potential_cols = ['actual_state_aid', 'actual_tax_levy']
    for col in potential_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# 4. UI
df_merged = add_metrics(get_data())

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ Select District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

page = st.sidebar.radio("Navigation", ["Financial Ledger", "Revenue Matrix"])

if sel_district != "Select...":
    if page == "Financial Ledger":
        st.title(f"📍 Ledger: {sel_district}")
        st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)
    elif page == "Revenue Matrix":
        target_cds = df_f[df_f['district_name'] == sel_district]['cds_code'].iloc[0]
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            st.dataframe(rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum'), use_container_width=True)