import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD & MERGE
df_sum = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")

df_sum["cds_code"] = df_sum["cds_code"].astype(str).str.zfill(6)
df_map["cds_code"] = df_map["cds_code"].astype(str).str.zfill(6)
df_types["cds_code"] = df_types["cds_code"].astype(str).str.zfill(6)

df_merged = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 3. CALCULATIONS
for col in ['actual_state_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation']:
    df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)
df_merged['YoY_State_Aid_Diff'] = df_merged.groupby('district_name')['actual_state_aid'].diff().fillna(0)
df_merged['Tax_Levy_per_100'] = (df_merged['actual_tax_levy'] / df_merged['equalized_valuation'].replace(0, 1)) * 100

# 4. UI FILTERS (Cascading)
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset"): st.rerun()

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].fillna("Unassigned").unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].fillna("Unassigned").unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna("Unassigned").unique().tolist()))

# Apply Cascading Logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

# 5. MATRIX
if sel_district != "Select...":
    df_render = df_f[df_f['district_name'] == sel_district].sort_values("fiscal_year")
    col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 
                 'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']
    st.dataframe(df_render[col_order], use_container_width=True)