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
    
    # 1. Standardize CDS_CODE (zfill to 6 characters)
    for df in [df_sum, df_map, df_meta]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # 2. Merge Legislative Mapping
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # 3. Merge Metadata (District Type/Name)
    # Check if df_meta has the necessary columns before merging
    if not df_meta.empty and 'cds_code' in df_meta.columns:
        cols = ['cds_code']
        if 'district_type' in df_meta.columns: cols.append('district_type')
        if 'district_name' in df_meta.columns: cols.append('district_name')
        
        df = df.merge(df_meta[cols], on='cds_code', how='left')
    
    # 4. Fill missing columns so filters always have data
    df['district_name'] = df.get('district_name', 'Unknown').fillna('Unknown')
    df['district_type'] = df.get('district_type', 'Unknown').fillna('Unknown')
    df['county_name'] = df.get('county_name', 'Unassigned').fillna('Unassigned')
    df['ld_display'] = df.get('ld_display', 'N/A').fillna('N/A')
    
    return df

# UI Setup
df_merged = get_data()

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].astype(str).unique().tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].astype(str).unique().tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].astype(str).unique().tolist()))

# Filter logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].astype(str).unique().tolist()))

st.title("🏛️ NJ School Finance Intelligence")
if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)