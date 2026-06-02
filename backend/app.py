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
    df_types = fetch_table("district_metadata_mapping") 

    # Standardize CDS codes
    for df in [df_sum, df_map, df_types]:
        col = 'cds' if 'cds' in df.columns else 'cds_code'
        if col in df.columns:
            df.rename(columns={col: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Perform Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # DYNAMIC MERGE: Check available columns in df_types before merging
    cols_to_merge = [c for c in ['cds_code', 'district_type', 'district_name'] if c in df_types.columns]
    
    # Diagnostic: Show us what columns actually exist
    st.sidebar.write("Available Metadata Columns:", df_types.columns.tolist())
    
    if len(cols_to_merge) > 1:
        df = df.merge(df_types[cols_to_merge], on='cds_code', how='left')
    else:
        st.sidebar.error(f"Cannot merge. Expected [cds_code, district_type, district_name], but found: {list(df_types.columns)}")
    
    df['district_name'] = df['district_name_y'].fillna(df['district_name_x']) if 'district_name_y' in df.columns else df['district_name_x']
    df['county_name'] = df['county_name'].fillna('Unassigned')
    df['district_type'] = df['district_type'].fillna('Unknown')
    
    return df

# UI Setup
df_merged = get_data()

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().astype(str).tolist()))

# Filtering logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().astype(str).tolist()))

# Display
st.title("🏛️ New Jersey School Finance Intelligence")
if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)