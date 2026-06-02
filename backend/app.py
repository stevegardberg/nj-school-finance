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
    
    # Ensure CDS_CODE is consistently string for merging
    for df in [df_sum, df_map, df_meta]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge: State Aid + Legislative Mapping
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # Merge: Metadata
    # We use a left merge to ensure we keep all records from state_aid_summary
    if not df_meta.empty:
        df = df.merge(df_meta[['cds_code', 'district_type', 'district_name']], on='cds_code', how='left', suffixes=('', '_meta'))
        # Prioritize metadata names if available, else keep summary names
        if 'district_name_meta' in df.columns:
            df['district_name'] = df['district_name_meta'].combine_first(df['district_name'])
    
    # Clean up columns to prevent dropdown/sorting errors
    df['district_name'] = df['district_name'].fillna('Unknown')
    df['county_name'] = df['county_name'].fillna('Unassigned')
    df['district_type'] = df['district_type'].fillna('Unknown')
    df['ld_display'] = df['ld_display'].fillna('N/A')
    
    return df

# Initialize Data
df_merged = get_data()

# Sidebar Filters
st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().tolist()))

# Filtering logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().tolist()))

# UI Display
st.title("🏛️ NJ School Finance Intelligence")
if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)