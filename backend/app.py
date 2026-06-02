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
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")
    
    # 1. Standardize CDS_CODE
    for df in [df_sum, df_map, df_meta]:
        if 'cds_code' in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # 2. Merge: Start with summary and legislative
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # 3. DYNAMIC MERGE: Only pick what exists
    expected_meta_cols = ['cds_code', 'district_type', 'district_name']
    available_cols = [c for c in expected_meta_cols if c in df_meta.columns]
    
    if len(available_cols) > 1: # Must have cds_code + at least one more
        df = df.merge(df_meta[available_cols], on='cds_code', how='left')
    
    # 4. Fill missing columns so UI components don't crash
    cols_to_ensure = ['district_name', 'county_name', 'district_type', 'ld_display']
    for col in cols_to_ensure:
        if col not in df.columns:
            df[col] = 'Unknown'
        else:
            df[col] = df[col].fillna('Unknown')
    
    return df

# Initialize Data
df_merged = get_data()

# 5. UI
st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].astype(str).unique().tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].astype(str).unique().tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].astype(str).unique().tolist()))

# Filter Logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].astype(str).unique().tolist()))

st.title("🏛️ NJ School Finance Intelligence")
if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)