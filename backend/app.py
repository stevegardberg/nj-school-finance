import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

# Immutable schema contract
REQUIRED_COLUMNS = {
    'state_aid_summary': ['cds_code', 'fiscal_year', 'district_name', 'actual_state_aid', 'actual_tax_levy', 
                          'adequacy_budget', 'uncapped_aid', 'local_fair_share', 'equalized_valuation', 'district_income', 'county_name'],
    'v_aggregated_enrollment': ['cds_code', 'fiscal_year', 'resident_enrollment'],
    'legislative_mapping': ['cds_code', 'ld_display'],
    'vw_district_cohorts': ['cds_code', 'district_type']
}

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

# Load and enforce schema
df_sum = fetch_table("state_aid_summary")[REQUIRED_COLUMNS['state_aid_summary']]
df_enroll = fetch_table("v_aggregated_enrollment")[REQUIRED_COLUMNS['v_aggregated_enrollment']]
df_map = fetch_table("legislative_mapping")[REQUIRED_COLUMNS['legislative_mapping']]
df_types = fetch_table("vw_district_cohorts")[REQUIRED_COLUMNS['vw_district_cohorts']]

# Cleanup
for df in [df_sum, df_enroll, df_map, df_types]:
    df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# Permanent Merge Contract
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map, on='cds_code', how='left')
df_merged = df_merged.merge(df_types, on='cds_code', how='left')

# Metrics
def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    for col in ['actual_state_aid', 'actual_tax_levy', 'equalized_valuation', 'resident_enrollment']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

df_merged = add_metrics(df_merged)

# UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
sel_district = st.selectbox("Select District:", sorted(df_merged['district_name'].dropna().unique().tolist()))

if sel_district:
    target = df_merged[df_merged['district_name'] == sel_district]
    st.dataframe(target, use_container_width=True)