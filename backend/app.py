import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?select=*&limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD
df_aid = fetch_table("state_aid_summary")
df_meta = fetch_table("district_metadata_mapping")
df_map = fetch_table("legislative_mapping")

# Normalize district names for bridging
def norm(val): return str(val).lower().strip()

df_aid['d_name_norm'] = df_aid['district_name'].apply(norm)
df_meta['d_name_norm'] = df_meta['district_name'].apply(norm)

# 3. BRIDGE MERGE (Using Name as the fallback key)
df_merged = df_aid.merge(
    df_meta[['d_name_norm', 'district_type']], 
    on='d_name_norm', 
    how='left'
)
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')

# 4. LAYOUT & FORMATTING
df_merged['district_type'] = df_merged['district_type'].fillna("Not Listed")
df_merged['ld_display'] = df_merged['ld_display'].fillna("Not Listed")

# UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

# Column Layout Fixes
c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().tolist()))

# Filtering
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)