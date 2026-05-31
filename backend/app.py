import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    res = requests.get(f"{BASE_URL}/{table}?select=*", headers=headers)
    if res.status_code != 200: return pd.DataFrame()
    return pd.DataFrame(res.json())

# LOAD DATA
df_aid = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_district_fte_summary")
df_map = fetch_table("legislative_mapping")
df_meta = fetch_table("district_metadata_mapping")

# CLEANING: Ensure CDS and Year are strings
def clean(df):
    if "cds_code" in df.columns: df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    if "fiscal_year" in df.columns: df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()
    return df

df_aid = clean(df_aid)
df_enroll = clean(df_enroll)
df_map = clean(df_map)
df_meta = clean(df_meta)

# 2. FULL OUTER MERGE (Prevents data loss)
# We start with Aid, merge everything else, keeping all records
df_merged = df_aid.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='outer')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')

# 3. UI FILTERS
st.markdown("### 🏛️ NJ School Finance Platform")

# Fill NAs to avoid crash and ensure visibility
df_merged['district_name'] = df_merged['district_name'].fillna("Unknown")
df_merged['ld_display'] = df_merged['ld_display'].fillna("Not Listed")
df_merged['district_type'] = df_merged['district_type'].fillna("Not Listed")

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].astype(str).unique().tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].astype(str).unique().tolist()))
sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].fillna("Unknown").astype(str).unique().tolist()))

# Filter
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

district_list = sorted(df_f['district_name'].astype(str).unique().tolist())
sel_district = c4.selectbox("District:", ["Select..."] + district_list)

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)