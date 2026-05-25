import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

if 'initialized' not in st.session_state:
    st.cache_data.clear()
    st.session_state['initialized'] = True

# 1. DATABASE HANDSHAKE
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
except Exception:
    st.error("🔒 Security credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/vw_district_cohorts",
    "revenue": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/revenue"
}

def fetch_supabase_table_data(base_url):
    all_records = []
    page = 0
    page_size = 1000  
    try:
        while True:
            url = f"{base_url}?limit={page_size}&offset={page * page_size}"
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                page_data = response.json()
                if not page_data: break
                all_records.extend(page_data)
                if len(page_data) < page_size: break
                page += 1
            else: break
        return all_records
    except: return []

# 2. DATA PIPELINE
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

raw_summary = fetch_supabase_table_data(URLS["summary"])
raw_mapping = fetch_supabase_table_data(URLS["mapping"])
raw_types = fetch_supabase_table_data(URLS["types"])
raw_revenue = fetch_supabase_table_data(URLS["revenue"])

df_summary = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

def secure_string_normalize(series):
    return series.astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

df_summary["join_key"] = secure_string_normalize(df_summary["cds_code"])
df_types["join_key"] = secure_string_normalize(df_types["cds_code"])

# 3. JOIN EXECUTION
df_joined = pd.merge(df_summary, df_types[["join_key", "district_name", "district_type"]], on="join_key", how="left")

# 4. FILTERS
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1: sel_ld = st.selectbox("Legislative Filter", ["All"] + sorted(list(df_joined["assigned_ld"].unique())))
with f_col4: sel_district = st.selectbox("Target District", ["Select..."] + sorted(list(df_joined["district_name"].dropna().unique())))

# 5. RENDER
st.markdown("---")
if sel_district != "Select...":
    st.write(f"Displaying data for {sel_district}")
else:
    st.info("Please select a district to view the ledger.")