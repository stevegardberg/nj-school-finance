import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(layout="wide")

# 1. SETUP & FETCH
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
URLS = {
    "Summary": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary",
    "Mapping": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping",
    "Types": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/district_metadata_mapping"
}

@st.cache_data(ttl=3600)
def fetch_all_data(url):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{url}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

df_summary = fetch_all_data(URLS["Summary"])
df_types = fetch_all_data(URLS["Types"])

# 2. CALCULATIONS
# Ensure numeric types
for col in ['actual_state_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation']:
    if col in df_summary.columns: df_summary[col] = pd.to_numeric(df_summary[col], errors='coerce')

# Logic for Change 4 & 5
df_summary = df_summary.sort_values(['district_name', 'fiscal_year'])
df_summary['YoY_State_Aid_Diff'] = df_summary.groupby('district_name')['actual_state_aid'].diff()
df_summary['Tax_Levy_per_100'] = (df_summary['actual_tax_levy'] / df_summary['equalized_valuation']) * 100

# 3. UI LAYOUT
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset"): st.rerun()

c1, c2, c3 = st.columns(3)
# Filters populate from the df_summary itself to ensure they aren't empty
sel_district = c1.selectbox("Target District:", sorted(df_summary['district_name'].unique().tolist()))

# 4. DISPLAY
df_render = df_summary[df_summary['district_name'] == sel_district]

# Define strict column order
col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 
             'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']

st.markdown(f"#### 📍 Ledger: {sel_district}")
st.dataframe(df_render[col_order], use_container_width=True)

st.markdown("#### 📊 Peer Group Analysis")
if not df_types.empty:
    peer_data = df_types[df_types['district_name'] == sel_district]
    st.write(peer_data)
else:
    st.warning("Peer group metadata currently unavailable.")