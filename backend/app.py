import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

API_KEY = st.secrets["headers"]["apikey"]
AUTH_TOKEN = st.secrets["headers"]["Authorization"]
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

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
    return pd.DataFrame(data)

# LOAD DATA
df_sum = fetch_all_data("state_aid_summary")

# TARGETED FETCH: Get ONLY the enrollment records we need for these districts
# This avoids the 3 million row scan
boonton_codes = '("270450","270460")'
enroll_url = f"{BASE_URL}/enrollment_master?cds_code=in.{boonton_codes}&apikey={API_KEY}"
res = requests.get(enroll_url, headers={"apikey": API_KEY, "Authorization": AUTH_TOKEN})
df_enroll_raw = pd.DataFrame(res.json())

# STANDARDIZE
for df in [df_sum, df_enroll_raw]:
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    if "fiscal_year" in df.columns: 
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# AGGREGATE
if not df_enroll_raw.empty:
    df_enroll_raw['student_count'] = pd.to_numeric(df_enroll_raw['student_count'], errors='coerce')
    df_enroll = df_enroll_raw.groupby(['cds_code', 'fiscal_year'])['student_count'].sum().reset_index()
else:
    df_enroll = pd.DataFrame(columns=['cds_code', 'fiscal_year', 'student_count'])

# MERGE
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')

# UI
st.markdown("### 🏛️ NJ School Finance Platform")
district_list = sorted(df_merged['district_name'].dropna().unique().tolist())
sel_district = st.selectbox("Select District:", ["Select..."] + district_list)

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)