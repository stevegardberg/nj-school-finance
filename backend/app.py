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
    df = pd.DataFrame(all_records)
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

# 1. Fetch
df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")

# 2. Merge
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')

# 3. DIAGNOSTIC PRINT
st.write(f"Total rows in merged dataframe: {len(df_merged)}")
st.write("First 5 rows of data:")
st.dataframe(df_merged.head())

# 4. Fallback Selection
if not df_merged.empty and 'district_name' in df_merged.columns:
    districts = sorted(df_merged['district_name'].dropna().unique().tolist())
    sel_district = st.selectbox("Select District:", ["Select..."] + districts)
else:
    st.error("No data found or 'district_name' column missing.")