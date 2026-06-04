import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ School Finance Intelligence")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200: return pd.DataFrame()
        data = res.json()
        if not data: break
        all_records.extend(data)
        page += 1
    return pd.DataFrame(all_records)

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")
    
    # Ensure CDS codes are 6-character strings
    for df in [df_sum, df_map, df_meta]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    df = df.merge(df_meta[['cds_code', 'district_type', 'district_name']], on='cds_code', how='left')
    
    # Fill missing values to ensure strings exist
    df['district_name'] = df['district_name'].fillna('Unknown District')
    df['county_name'] = df['county_name'].fillna('Unknown County')
    df['district_type'] = df['district_type'].fillna('Unknown Type')
    df['ld_display'] = df['ld_display'].fillna('N/A')
    
    # Create the display label that will show in the dropdown
    df['display_name'] = df['district_name'] + " (" + df['county_name'] + ")"
    return df

def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    numeric_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                    'equalized_valuation', 'local_fair_share', 'district_income']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def get_formatted_matrix(df):
    rename_map = {'fiscal_year': 'Fiscal Year', 'actual_state_aid': 'Actual Aid', 'actual_tax_levy': 'Actual Levy'}
    df_out = df.rename(columns=rename_map)
    return df_out

# UI Execution
df_merged = add_metrics(get_data())

st.markdown("### 🏛️ NJ School Finance Intelligence")

if df_merged.empty:
    st.error("No data loaded. Check Supabase connection.")
else:
    c1, c2, c3, c4 = st.columns(4)
    
    # Populate Filters
    sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
    sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().tolist()))
    sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().tolist()))

    # Apply Filters
    df_f = df_merged.copy()
    if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
    if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
    if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

    # Populate 4th dropdown
    districts = ["Select..."] + sorted(df_f['display_name'].unique().tolist())
    sel_district = c4.selectbox("4️⃣ District:", options=districts)

    if sel_district != "Select...":
       target_data = df_f[df_f['display_name'] == sel_district]
       st.subheader(f"📍 Financial Ledger: {sel_district}")
       st.dataframe(get_formatted_matrix(target_data), use_container_width=True)

#