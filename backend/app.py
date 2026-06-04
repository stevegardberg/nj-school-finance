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
        if res.status_code != 200: return pd.DataFrame()
        data = res.json()
        if not data: break
        all_records.extend(data)
        page += 1
    return pd.DataFrame(all_records)

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")
    
    if df_sum.empty: return pd.DataFrame()

    for df in [df_sum, df_map, df_meta]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    required_meta = ['cds_code', 'district_type', 'district_name']
    if all(col in df_meta.columns for col in required_meta):
        df = df.merge(df_meta[required_meta], on='cds_code', how='left')
    else:
        df['district_type'] = 'Unknown'
        df['district_name'] = 'Unknown'

    for col, default in [('district_type', 'Unknown'), ('district_name', 'Unknown'), 
                         ('county_name', 'Unassigned'), ('ld_display', 'N/A')]:
        if col not in df.columns: df[col] = default
        else: df[col] = df[col].fillna(default)
            
    df['display_name'] = df['district_name'].astype(str) + " (" + df['county_name'].astype(str) + ")"
    return df

# UI Execution
df_merged = get_data()

st.markdown("### 🏛️ NJ School Finance Intelligence")

if df_merged.empty:
    st.error("Data is empty. Please check your Supabase tables.")
else:
    # Get distinct options from the full dataset
    ld_opts = sorted([str(x) for x in df_merged['ld_display'].unique() if x])
    type_opts = sorted([str(x) for x in df_merged['district_type'].unique() if x])
    county_opts = sorted([str(x) for x in df_merged['county_name'].unique() if x])

    c1, c2, c3, c4 = st.columns(4)
    sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + ld_opts)
    sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + type_opts)
    sel_county = c3.selectbox("3️⃣ County:", ["All"] + county_opts)

    # Filter logic
    df_f = df_merged.copy()
    if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
    if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
    if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

    # Show diagnostic of remaining rows
    st.sidebar.info(f"Districts in view: {len(df_f['display_name'].unique())}")
    
    sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['display_name'].unique().tolist()))