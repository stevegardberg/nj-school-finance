import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP & FETCH
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
# Start with base Aid Summary
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')

# Merge mapping (using suffixes to prevent column collision)
df_merged = df_merged.merge(df_map, on='cds_code', how='left', suffixes=('', '_map'))

# Merge cohorts
df_merged = df_merged.merge(df_types, on='cds_code', how='left', suffixes=('', '_cohorts'))

# 5. DATA CLEANUP (Prevent AttributeErrors)
df_merged['county_name'] = df_merged['county_name'].fillna('Unknown')
df_merged['ld_display'] = df_merged.get('ld_display', pd.Series(['Unknown']*len(df_merged))).fillna('Unknown')
df_merged['district_type'] = df_merged.get('district_type', pd.Series(['Unknown']*len(df_merged))).fillna('Unknown')
df_merged['resident_enrollment'] = df_merged.get('resident_enrollment', pd.Series([0]*len(df_merged))).fillna(0)

# 6. CALCULATIONS
def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    # Numeric conversion
    num_cols = ['actual_state_aid', 'actual_tax_levy', 'equalized_valuation', 'resident_enrollment']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    return df

df_merged = add_metrics(df_merged)

# 7. FORMATTING & UI
def get_formatted_matrix(df):
    # (Rest of your original formatting logic here)
    return df

st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
# ... (Dropdown and Display logic)