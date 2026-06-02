import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    try:
        res = requests.get(f"{BASE_URL}/{table}?limit=10000", headers=headers)
        if res.status_code == 200 and res.json():
            return pd.DataFrame(res.json())
        return pd.DataFrame() # Return empty if no data
    except:
        return pd.DataFrame()

# 2. LOAD & MERGE
df_sum = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_meta = fetch_table("district_metadata_mapping")

# Ensure metadata exists even if fetch was empty
required_cols = ['cds_code', 'district_type', 'district_name']
for col in required_cols:
    if col not in df_meta.columns:
        df_meta[col] = None

# Ensure keys are strings
for df in [df_sum, df_map, df_meta]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

# Perform Merge safely
df_merged = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
df_merged = df_merged.merge(df_meta[required_cols], on='cds_code', how='left')

# 3. CALCULATIONS
potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                  'equalized_valuation', 'local_fair_share', 'district_income']

for col in potential_cols:
    if col in df_merged.columns:
        df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)
    else:
        df_merged[col] = 0.0

# 4. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

# Ensure columns exist for dropdowns
if 'ld_display' not in df_merged.columns: df_merged['ld_display'] = 'N/A'
if 'district_type' not in df_merged.columns: df_merged['district_type'] = 'N/A'
if 'county_name' not in df_merged.columns: df_merged['county_name'] = 'N/A'
if 'district_name' not in df_merged.columns: df_merged['district_name'] = 'Unknown'

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)