import streamlit as st
import requests
import pandas as pd
import re

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}

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

# 2. DATA LOAD
df_sum = fetch_all_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary")
df_map = fetch_all_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping")

# 3. MERGE & CALCULATE
df_merged = df_sum.merge(df_map[['cds_code', 'legislative_district']], on='cds_code', how='left')
for col in ['actual_state_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation']:
    df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

df_merged = df_merged.sort_values(['district_name', 'fiscal_year'])
df_merged['YoY_State_Aid_Diff'] = df_merged.groupby('district_name')['actual_state_aid'].diff().fillna(0)
df_merged['Tax_Levy_per_100'] = (df_merged['actual_tax_levy'] / df_merged['equalized_valuation'].replace(0, 1)) * 100

# 4. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset"): st.rerun()

c1, c2, c3, c4 = st.columns(4)
ld_options = sorted([str(x) for x in df_merged['legislative_district'].dropna().unique()])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + ld_options)
sel_type = c2.selectbox("2️⃣ District Type:", ["All", "Unassigned"])
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().tolist()))

# Cascade logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['legislative_district'].astype(str) == sel_ld]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]
sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

# 5. MATRIX DISPLAY
if sel_district != "Select...":
    df_render = df_f[df_f['district_name'] == sel_district]
    # Enforced Column Order
    col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 
                 'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']
    st.markdown(f"#### 📍 Ledger: {sel_district}")
    st.dataframe(df_render[col_order], use_container_width=True)