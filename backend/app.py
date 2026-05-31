import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP & FETCH
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    res = requests.get(f"{BASE_URL}/{table}?select=*", headers=headers)
    if res.status_code != 200: return pd.DataFrame()
    df = pd.DataFrame(res.json())
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

# LOAD DATA
df_sum = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")
df_total_enroll = fetch_table("v_district_fte_summary")

# STANDARDIZE KEYS
for df in [df_sum, df_map, df_types, df_total_enroll]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 2. MERGE (Safety-Net Logic)
df_merged = df_sum.merge(df_total_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# FILL NA to ensure rows aren't dropped by filters
df_merged['ld_display'] = df_merged['ld_display'].fillna("Not Listed")
df_merged['district_type'] = df_merged['district_type'].fillna("Not Listed")
df_merged['county_name'] = df_merged['county_name'].fillna("Unknown")
df_merged['district_name'] = df_merged['district_name'].fillna("Unknown")

# 3. CALCULATIONS
potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy', 
                  'equalized_valuation', 'local_fair_share', 'district_income', 'resident_enrollment']
for col in potential_cols:
    if col in df_merged.columns:
        df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

# 4. UI FILTERS
st.markdown("### 🏛️ NJ School Finance Platform")

# Debugging visibility: Show this if Boonton data exists in the merged result
if not df_merged[df_merged['district_name'].str.contains("Boonton", na=False)].empty:
    st.info("Boonton Town/Twp data loaded and available.")

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().astype(str).tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].unique().astype(str).tolist()))
sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].unique().astype(str).tolist()))

# Filter logic with explicit string casting
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

# Ensure district_name is string for the dropdown to avoid TypeError
district_list = sorted(df_f['district_name'].astype(str).unique().tolist())
sel_district = c4.selectbox("District:", ["Select..."] + district_list)

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(target_data, use_container_width=True)