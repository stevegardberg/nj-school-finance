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
    # Corrected table name based on your schema audit
    df_types = fetch_table("district_metadata_mapping") 

    for df in [df_sum, df_map, df_types]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Perform Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    df = df.merge(df_types[['cds_code', 'district_type', 'district_name']], on='cds_code', how='left')
    
    # Clean up merged names
    df['district_name'] = df['district_name_y'].fillna(df['district_name_x'])
    df['county_name'] = df['county_name'].fillna('Unassigned')
    df['district_type'] = df['district_type'].fillna('Unknown')
    
    return df

# UI Setup
df_merged = get_data()

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().astype(str).tolist()))

# Filter Logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().astype(str).tolist()))

# Page Logic
st.title("🏛️ New Jersey School Finance Intelligence")
page = st.radio("Navigation", ["Financial Ledger", "Revenue Matrix"], horizontal=True)

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    if page == "Financial Ledger":
        st.subheader(f"📍 Financial Ledger: {sel_district}")
        st.dataframe(target_data, use_container_width=True)
    else:
        target_cds = target_data['cds_code'].iloc[0]
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            st.dataframe(rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum'), use_container_width=True)
        else:
            st.info("No revenue data found.")