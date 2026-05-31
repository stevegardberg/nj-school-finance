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
    df = pd.DataFrame(all_records)
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

# 2. LOAD DATA
df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")

# 3. STANDARDIZE KEYS
for df in [df_sum, df_enroll, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 4. CLEAN MERGE
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 5. DEFENSIVE CLEANUP
df_merged['county_name'] = df_merged.get('county_name', pd.Series(['Unknown']*len(df_merged))).fillna('Unknown')
df_merged['ld_display'] = df_merged.get('ld_display', pd.Series(['Unknown']*len(df_merged))).fillna('Unknown')
df_merged['district_type'] = df_merged.get('district_type', pd.Series(['Unknown']*len(df_merged))).fillna('Unknown')

# 6. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

# Populate districts safely
if 'district_name' in df_merged.columns:
    districts = sorted([str(d) for d in df_merged['district_name'].dropna().unique() if d and d != 'nan'])
    sel_district = st.selectbox("Select District:", ["Select..."] + districts)

    if sel_district != "Select...":
        target = df_merged[df_merged['district_name'].astype(str) == sel_district]
        st.subheader(f"📍 Financial Ledger: {sel_district}")
        st.dataframe(target, use_container_width=True)
else:
    st.error("District name data not found.")