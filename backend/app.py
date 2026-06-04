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
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_meta = fetch_table("district_metadata_mapping")
    
    # Standardize CDS keys
    for df in [df_sum, df_map, df_meta]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge Process:
    # 1. Base Summary + Legislative (brings in county_name, ld_display)
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    
    # 2. Merge + Metadata (brings in district_type)
    if 'cds_code' in df_meta.columns:
        df = df.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')

    # Force initialization of UI columns to prevent 'Unassigned' or empty dropdowns
    df['district_type'] = df.get('district_type', 'Unknown Type').fillna('Unknown Type')
    df['county_name'] = df.get('county_name', 'Unknown County').fillna('Unknown County')
    df['ld_display'] = df.get('ld_display', 'N/A').fillna('N/A')
    df['district_name'] = df['district_name'].fillna('Unknown District')
    
    return df

def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    numeric_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                    'equalized_valuation', 'local_fair_share', 'district_income']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

def get_formatted_matrix(df):
    rename_map = {'fiscal_year': 'Fiscal Year', 'actual_state_aid': 'Actual Aid', 'actual_tax_levy': 'Actual Levy'}
    return df.rename(columns=rename_map)

# UI
df_merged = add_metrics(get_data())
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

if df_merged.empty:
    st.error("No data loaded. Check your Supabase tables.")
else:
    c1, c2, c3, c4 = st.columns(4)
    # Filter dropdowns populated from full dataset
    sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
    sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().tolist()))
    sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().tolist()))

    df_f = df_merged.copy()
    if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
    if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
    if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

    sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().tolist()))

    if sel_district != "Select...":
       st.subheader(f"📍 Financial Ledger: {sel_district}")
       st.dataframe(get_formatted_matrix(df_f[df_f['district_name'] == sel_district]), use_container_width=True)