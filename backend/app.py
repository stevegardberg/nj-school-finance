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
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map.rename(columns={'county_name': 'county_name_map'}), on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# CLEAN UP DUPLICATE COLUMNS
# If district_name_x exists, use it as the master, otherwise look for district_name_y
if 'district_name_x' in df_merged.columns:
    df_merged['district_name'] = df_merged['district_name_x']
elif 'district_name_y' in df_merged.columns:
    df_merged['district_name'] = df_merged['district_name_y']
elif 'district_name' in df_merged.columns:
    pass # Already exists
else:
    df_merged['district_name'] = "Unknown District"

# 5. CALCULATIONS
def add_metrics(df):
    num_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation', 'local_fair_share', 'district_income', 'resident_enrollment']
    for col in num_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

df_merged = add_metrics(df_merged)

# 6. FORMATTING
def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 'local_fair_share', 'actual_tax_levy', 'equalized_valuation', 'resident_enrollment']
    available_cols = [c for c in col_order if c in df.columns]
    df_out = df[available_cols].copy()
    rename_map = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid', 'actual_state_aid': 'Actual Aid', 'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'equalized_valuation': 'Equalized Valuation', 'resident_enrollment': 'Resident Enrollment'}
    df_out = df_out.rename(columns=rename_map)
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${float(x):,.0f}" if 'Enrollment' not in col else f"{float(x):,.0f}")
    return df_out

# 7. UI
st.markdown("### 🏛️ NJ School Finance Platform")
district_list = sorted(df_merged['district_name'].dropna().unique().tolist())
sel_district = st.selectbox("Select District:", ["Select..."] + district_list)

if sel_district != "Select...":
    target_data = df_merged[df_merged['district_name'] == sel_district].sort_values('fiscal_year')
    st.subheader(f"📍 Ledger: {sel_district}")
    st.dataframe(get_formatted_matrix(target_data), use_container_width=True)