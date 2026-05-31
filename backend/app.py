import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

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

# 1. Load Data
df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")

# 2. Normalize
for df in [df_sum, df_enroll, df_map, df_types]:
    df.columns = [str(c).lower().strip() for c in df.columns]
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 3. Additive Merge
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left', suffixes=('', '_map'))
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 4. DEFENSIVE CLEANUP
# If 'county_name' doesn't exist, create it from the other table or set to 'Unknown'
if 'county_name' not in df_merged.columns:
    df_merged['county_name'] = 'Unknown'
else:
    df_merged['county_name'] = df_merged['county_name'].fillna('Unknown')

df_merged['ld_display'] = df_merged.get('ld_display', 'Unknown').fillna('Unknown')
df_merged['district_type'] = df_merged.get('district_type', 'Unknown').fillna('Unknown')

# 5. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
# ... (rest of your UI remains the same)