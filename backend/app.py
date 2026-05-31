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

# 3. STANDARDIZE KEYS (CDS Code is the source of truth)
for df in [df_sum, df_enroll, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 4. MERGE ON CDS CODE ONLY
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 5. UI - CDS CODE ANCHORED SELECTION
st.markdown("### 🏛️ NJ School Finance Platform")

# Create a clean display label while keeping CDS Code as the unique selector
df_merged['display_label'] = df_merged['district_name'] + " (" + df_merged['cds_code'] + ")"
unique_districts = df_merged[['display_label', 'cds_code']].drop_duplicates().dropna().sort_values('display_label')

sel_option = st.selectbox("Select District:", ["Select..."] + unique_districts['display_label'].tolist())

if sel_option != "Select...":
    # Pull the CDS code back out of the label to filter the data
    target_cds = unique_districts[unique_districts['display_label'] == sel_option]['cds_code'].values[0]
    target_data = df_merged[df_merged['cds_code'] == target_cds].sort_values('fiscal_year')
    
    st.subheader(f"📍 Financial Ledger: {sel_option}")
    st.dataframe(target_data, use_container_width=True)