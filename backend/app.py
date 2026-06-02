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
df_meta = fetch_table("district_metadata_mapping")

# Ensure keys are strings and standardized
for df in [df_sum, df_map, df_meta]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)

# Merge exactly as the schema requires
df_merged = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
df_merged = df_merged.merge(df_meta[['cds_code', 'district_type', 'district_name']], on='cds_code', how='left')

# 3. CALCULATIONS
potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                  'equalized_valuation', 'local_fair_share', 'district_income']

for col in potential_cols:
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
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
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
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)