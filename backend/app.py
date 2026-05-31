import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
API_KEY = st.secrets["headers"]["apikey"]
AUTH_TOKEN = st.secrets["headers"]["Authorization"]
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

# Force a paginated fetch to ensure NO rows are truncated
@st.cache_data(ttl=3600)
def fetch_all_data(table):
    data = []
    page = 0
    size = 1000
    while True:
        url = f"{BASE_URL}/{table}?apikey={API_KEY}&limit={size}&offset={page * size}"
        headers = {"apikey": API_KEY, "Authorization": AUTH_TOKEN}
        res = requests.get(url, headers=headers)
        if res.status_code != 200 or not res.json(): break
        batch = res.json()
        data.extend(batch)
        if len(batch) < size: break
        page += 1
    df = pd.DataFrame(data)
    if not df.empty:
        df.columns = [str(c).lower().strip() for c in df.columns]
    return df

# 2. LOAD DATA
df_sum = fetch_all_data("state_aid_summary")
df_enroll = fetch_all_data("v_aggregated_enrollment")
df_map = fetch_all_data("legislative_mapping") # Fixed function call
df_types = fetch_all_data("vw_district_cohorts")

# 3. STANDARDIZE KEYS
for df in [df_sum, df_enroll, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

# 4. DEBUGGING
st.sidebar.write("### Data Integrity Check")
boonton_codes = ['270450', '270460']
for name, df in [("Summary", df_sum), ("Enrollment", df_enroll), ("Mapping", df_map)]:
    if "cds_code" in df.columns:
        count = len(df[df['cds_code'].isin(boonton_codes)])
        st.sidebar.write(f"{name} has {count} Boonton records.")

# 5. MERGE
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')

# 6. UI
st.markdown("### 🏛️ NJ School Finance Platform")
df_merged['display_label'] = df_merged['district_name'].fillna('Unknown') + " (" + df_merged['cds_code'] + ")"
unique_districts = sorted(df_merged['display_label'].dropna().unique().tolist())

sel_option = st.selectbox("Select District:", ["Select..."] + unique_districts)

if sel_option != "Select...":
    target_cds = sel_option.split('(')[-1].replace(')', '')
    target_data = df_merged[df_merged['cds_code'] == target_cds].sort_values('fiscal_year')
    st.dataframe(target_data, use_container_width=True)