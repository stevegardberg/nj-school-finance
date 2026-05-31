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

# 2. Normalize
for df in [df_sum, df_map, df_types, df_enroll]:
    df.columns = [str(c).lower().strip() for c in df.columns]
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 3. Step-wise Merge
# A. Join Yearly data first
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')

# B. Join Static Metadata second (Only on cds_code)
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 4. Calculations
def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    # Ensure numeric types
    for col in ['actual_state_aid', 'actual_tax_levy', 'uncapped_aid', 'local_fair_share', 'equalized_valuation']:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)
    
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

df_merged = add_metrics(df_merged)

# 5. Formatter
def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 'Over_Under_Funded', 
                 'Pct_Change_Aid', 'local_fair_share', 'actual_tax_levy', 'Over_Under_LFS', 
                 'Pct_Change_Levy', 'equalized_valuation', 'Tax_Levy_per_100', 'district_income', 'resident_enrollment']
    available_cols = [c for c in col_order if c in df.columns]
    df_out = df[available_cols].copy().rename(columns={
        'fiscal_year': 'Fiscal Year', 'actual_state_aid': 'Actual Aid', 'resident_enrollment': 'Resident Enrollment'
    })
    return df_out

# 6. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
sel_district = st.selectbox("Select District:", sorted(df_merged['district_name'].dropna().unique().tolist()))
if sel_district:
    target_data = df_merged[df_merged['district_name'] == sel_district]
    st.dataframe(get_formatted_matrix(target_data), use_container_width=True)