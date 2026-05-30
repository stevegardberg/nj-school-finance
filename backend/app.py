import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    res = requests.get(f"{BASE_URL}/{table}?select=*", headers=headers)
    if res.status_code != 200: return pd.DataFrame()
    df = pd.DataFrame(res.json())
    # FORCE LOWERCASE IMMEDIATELY
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

# 1. LOAD DATA
df_sum = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")
df_total_enroll = fetch_table("v_district_fte_summary")

# VALIDATION: Check for required keys
for name, df in [("state_aid", df_sum), ("enrollment_view", df_total_enroll)]:
    if 'cds_code' not in df.columns or 'fiscal_year' not in df.columns:
        st.error(f"CRITICAL: {name} is missing keys. Found columns: {df.columns.tolist()}")
        st.stop()

# Standardize keys
for df in [df_sum, df_map, df_types, df_total_enroll]:
    df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)

# 2. MERGE
df_merged = df_sum.merge(df_total_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 3. CALCULATIONS
potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy', 
                  'equalized_valuation', 'local_fair_share', 'district_income', 'resident_enrollment']
for col in potential_cols:
    if col in df_merged.columns:
        df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

df_merged = add_metrics(df_merged)

# 4. UI
st.markdown("### 🏛️ NJ School Finance Platform (Optimized)")
c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().tolist()))
sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(target_data, use_container_width=True)