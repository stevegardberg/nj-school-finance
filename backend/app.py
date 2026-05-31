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
st.write("Available columns in merged dataframe:", df_merged.columns.tolist())
st.dataframe(df_merged.head())

# 4. Corrected Selection Logic
# If 'district_name' is missing, check if it's 'name' or 'districtname'
col_options = ['district_name', 'name', 'districtname']
actual_col = next((c for c in col_options if c in df_merged.columns), None)

if actual_col:
    st.write(f"Using '{actual_col}' as the district identifier.")
    districts = sorted(df_merged[actual_col].dropna().unique().tolist())
    sel_district = st.selectbox("Select District:", ["Select..."] + districts)
else:
    st.error("Critical Error: Could not find a district name column in the merged data.")