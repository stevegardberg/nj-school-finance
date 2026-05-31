import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?select=*&limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 1. Load Data
df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")

# 2. Normalize Keys
for df in [df_sum, df_enroll, df_map, df_types]:
    df.columns = [str(c).lower().strip() for c in df.columns]
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 3. Additive Merge
# Ensure we keep all aid records by using df_sum as the base
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_merged = df_merged.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# Fill gaps so filters don't break
df_merged['ld_display'] = df_merged['ld_display'].fillna('Unknown')
df_merged['district_type'] = df_merged['district_type'].fillna('Unknown')
df_merged['county_name'] = df_merged['county_name'].fillna('Unknown')

# 4. Dashboard UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

c1, c2, c3, c4 = st.columns(4)

# Create filter options
lds = ["All"] + sorted(df_merged['ld_display'].unique().tolist())
types = ["All"] + sorted(df_merged['district_type'].unique().tolist())
counties = ["All"] + sorted(df_merged['county_name'].unique().tolist())

sel_ld = c1.selectbox("1️⃣ Legislative:", lds)
sel_type = c2.selectbox("2️⃣ District Type:", types)
sel_county = c3.selectbox("3️⃣ County:", counties)

# Filter Logic
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().tolist()))

if sel_district != "Select...":
    target = df_f[df_f['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(target, use_container_width=True)