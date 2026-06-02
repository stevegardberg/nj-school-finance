import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ School Finance Intelligence")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    try:
        res = requests.get(f"{BASE_URL}/{table}?limit=20000", headers=headers)
        if res.status_code == 200:
            return pd.DataFrame(res.json())
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")
    
    # Standardize CDS_CODE
    for df in [df_sum, df_map, df_meta]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # Merge Metadata if possible
    if not df_meta.empty:
        df = df.merge(df_meta[['cds_code', 'district_type', 'district_name']], on='cds_code', how='left')
    
    # SAFE FILLING: Ensure the columns exist as Series before calling .fillna()
    for col in ['district_name', 'district_type', 'county_name', 'ld_display']:
        if col not in df.columns:
            df[col] = 'Unknown'
        else:
            df[col] = df[col].fillna('Unknown')
            
    return df

# UI Logic
df_merged = get_data()

st.sidebar.header("Filter Settings")
# Use the cleaned columns
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().tolist()))

# Filter
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().tolist()))

st.title("🏛️ NJ School Finance Intelligence")
if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)