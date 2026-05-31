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

# 1. Load Tables
df_sum = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")
df_enroll = fetch_table("v_aggregated_enrollment")

# 2. Normalize and Validate
for name, df in [("sum", df_sum), ("map", df_map), ("types", df_types), ("enroll", df_enroll)]:
    if df.empty:
        st.error(f"Table '{name}' is empty! Check Supabase API.")
        st.stop()
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # Ensure keys exist
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 3. Step-wise Merge with explicit validation
if 'cds_code' not in df_sum.columns or 'fiscal_year' not in df_sum.columns:
    st.error(f"Missing keys in df_sum: {df_sum.columns.tolist()}")
    st.stop()

if 'cds_code' not in df_enroll.columns or 'fiscal_year' not in df_enroll.columns:
    st.error(f"Missing keys in df_enroll: {df_enroll.columns.tolist()}")
    st.stop()

df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 4. Formatting logic...
def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'actual_state_aid', 'resident_enrollment']
    return df[col_order].rename(columns={'fiscal_year': 'Fiscal Year', 'actual_state_aid': 'Actual Aid', 'resident_enrollment': 'Enrollment'})

# 5. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
sel_district = st.selectbox("Select District:", sorted(df_merged['district_name'].dropna().unique().tolist()))
if sel_district:
    target = df_merged[df_merged['district_name'] == sel_district]
    st.dataframe(get_formatted_matrix(target), use_container_width=True)