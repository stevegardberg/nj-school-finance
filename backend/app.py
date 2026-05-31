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
        # Use pagination to ensure we get ALL rows regardless of size
        res = requests.get(f"{BASE_URL}/{table}?select=*&limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD & CLEAN
df_aid = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_meta = fetch_table("district_metadata_mapping")
df_enroll = fetch_table("v_district_fte_summary")

# Standardize columns to lowercase
for df in [df_aid, df_map, df_meta, df_enroll]:
    df.columns = [str(c).lower().strip() for c in df.columns]
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 3. MERGE
df_merged = df_aid.copy()
# Merge using left joins - now that we have ALL data, this is safe
if not df_enroll.empty:
    df_merged = df_merged.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
if not df_map.empty:
    df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
if not df_meta.empty:
    df_merged = df_merged.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')

# Fill missing metadata
df_merged['district_name'] = df_merged['district_name'].fillna("Unknown")
df_merged['ld_display'] = df_merged.get('ld_display', 'Not Listed').fillna("Not Listed")
df_merged['district_type'] = df_merged.get('district_type', 'Not Listed').fillna("Not Listed")
df_merged['county_name'] = df_merged.get('county_name', 'Unknown').fillna("Unknown")

# 4. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")
c1, c2, c3, c4 = st.columns(4)

sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().tolist()))
sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)