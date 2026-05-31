import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
API_KEY = st.secrets["headers"]["apikey"]
AUTH_TOKEN = st.secrets["headers"]["Authorization"]
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    try:
        url = f"{BASE_URL}/{table}?apikey={API_KEY}"
        headers = {"apikey": API_KEY, "Authorization": AUTH_TOKEN, "Prefer": "return=representation"}
        res = requests.get(url, headers=headers, timeout=60)
        if res.status_code != 200: return pd.DataFrame()
        data = res.json()
        if not data: return pd.DataFrame()
        if isinstance(data, dict): data = [data]
        df = pd.DataFrame(data)
        df.columns = [str(c).lower().strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

# 2. LOAD DATA
df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")

# 3. STANDARDIZE KEYS
for df in [df_sum, df_enroll, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 4. ROBUST MERGE
# Start with df_sum as the base to keep ALL district records
df_merged = df_sum.copy()
df_merged = df_merged.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map.rename(columns={'county_name': 'county_name_map'}), on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# CONSOLIDATE DISTRICT NAMES
# If x and y exist, x is usually the master from df_sum
df_merged['district_name'] = df_merged['district_name_x'].fillna(df_merged.get('district_name_y', 'Unknown'))

# 5. UI DEBUGGING
# Remove this block later, but it will tell us if Boonton is actually in the final merged data
if st.sidebar.checkbox("Verify Boonton existence"):
    boonton_check = df_merged[df_merged['district_name'].str.contains("Boonton", na=False)]
    st.sidebar.write("Boonton records found:", len(boonton_check))
    st.sidebar.write(boonton_check[['district_name', 'cds_code']].drop_duplicates())

# 6. CALCULATIONS
num_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation', 'local_fair_share', 'district_income', 'resident_enrollment']
for col in num_cols:
    if col in df_merged.columns: df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

# 7. UI
st.markdown("### 🏛️ NJ School Finance Platform")
district_list = sorted(df_merged['district_name'].dropna().unique().tolist())
sel_district = st.selectbox("Select District:", ["Select..."] + district_list)

if sel_district != "Select...":
    target_data = df_merged[df_merged['district_name'] == sel_district].sort_values('fiscal_year')
    st.subheader(f"📍 Ledger: {sel_district}")
    # Display the ledger
    st.dataframe(target_data, use_container_width=True)