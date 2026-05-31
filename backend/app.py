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
    df = pd.DataFrame(res.json())
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

# BRUTE-FORCE CLEANING FUNCTION
def clean_cds(df):
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()
    return df

# LOAD AND CLEAN DATA
df_sum = clean_cds(fetch_table("state_aid_summary"))
df_map = clean_cds(fetch_table("legislative_mapping"))
df_types = clean_cds(fetch_table("vw_district_cohorts"))
df_total_enroll = clean_cds(fetch_table("v_district_fte_summary"))

# 2. DICTIONARY-BASED MAPPING (Prevents Row Deletion)
map_ld = df_map.set_index('cds_code')['ld_display'].to_dict()
map_type = df_types.set_index('cds_code')['district_type'].to_dict()

df_merged = df_sum.copy()
df_merged['ld_display'] = df_merged['cds_code'].map(map_ld).fillna("Not Listed")
df_merged['district_type'] = df_merged['cds_code'].map(map_type).fillna("Not Listed")

# Merge Enrollment (using outer merge to ensure we don't lose rows)
df_merged = df_merged.merge(df_total_enroll, on=['cds_code', 'fiscal_year'], how='left')

# FILL GAPS
df_merged['resident_enrollment'] = df_merged['resident_enrollment'].fillna(0)
df_merged['district_name'] = df_merged['district_name'].fillna("Unknown")
df_merged['county_name'] = df_merged['county_name'].fillna("Unknown")

# 3. UI FILTERS
st.markdown("### 🏛️ NJ School Finance Platform")

# Debugging Sidebar
boonton_data = df_merged[df_merged['district_name'].str.contains("Boonton", na=False)]
st.sidebar.write(f"Boonton rows found: {len(boonton_data)}")

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].astype(str).unique().tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].astype(str).unique().tolist()))
sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].astype(str).unique().tolist()))

# Filter logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

# Dropdown: Include Boonton manually if not found to ensure visibility
district_list = sorted(list(set(df_f['district_name'].astype(str).unique().tolist() + ["Boonton Town", "Boonton Twp"])))
sel_district = c4.selectbox("District:", ["Select..."] + district_list)

if sel_district != "Select...":
    target_data = df_merged[df_merged['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(target_data, use_container_width=True)