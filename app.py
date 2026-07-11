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

@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_types = fetch_table("vw_district_cohorts")

    # Standardize to lowercase
    df_sum.columns = df_sum.columns.str.lower()
    df_map.columns = df_map.columns.str.lower()
    df_types.columns = df_types.columns.str.lower()

    # Map mapping variations to standard names
    if 'cds_code' in df_map.columns: df_map = df_map.rename(columns={'cds_code': 'cds'})
    if 'cds_code' in df_types.columns: df_types = df_types.rename(columns={'cds_code': 'cds'})

    # Ensure CDS is a string to prevent merge mismatches
    df_sum['cds'] = df_sum['cds'].astype(str)
    df_map['cds'] = df_map['cds'].astype(str)
    df_types['cds'] = df_types['cds'].astype(str)

    # Perform merges
    df_merged = df_sum.merge(df_map[['cds', 'ld_display']], on='cds', how='left')
    df_merged = df_merged.merge(df_types[['cds', 'district_type']], on='cds', how='left')
    
    # Fill missing identifiers
    if 'county_name' not in df_merged.columns: df_merged['county_name'] = 'Unassigned'
    if 'district_type' not in df_merged.columns: df_merged['district_type'] = 'Unknown'
        
    return df_merged

def add_metrics(df):
    if 'district_name' not in df.columns: df['district_name'] = 'Unknown'
    df = df.sort_values(['district_name', 'fiscal_year'])
    
    num_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                'equalized_valuation', 'local_fair_share', 'district_income']
    for col in num_cols:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 'Over_Under_Funded',
                 'Pct_Change_Aid', 'local_fair_share', 'actual_tax_levy', 'Over_Under_LFS',
                 'Pct_Change_Levy', 'equalized_valuation', 'Tax_Levy_per_100', 'district_income']
    df_out = df[[c for c in col_order if c in df.columns]].copy()
    rename = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid',
              'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded', 'Pct_Change_Aid': '% Change Actual Aid',
              'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS',
              'Pct_Change_Levy': '% Change Actual Levy', 'equalized_valuation': 'Equalized Valuation',
              'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income'}
    df_out = df_out.rename(columns=rename)
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${float(x):,.0f}" if '%' not in col and 'per $100' not in col.lower() else (f"{float(x):.2%}" if '%' in col else (f"{float(x):.4f}" if 'per $100' in col.lower() else f"{float(x):,.0f}")))
    return df_out

df_merged = add_metrics(get_data())
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
    target = df_f[df_f['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(get_formatted_matrix(target), use_container_width=True, hide_index=True)
    for name, group_col, val in [("Legislative District", 'ld_display', target['ld_display'].iloc[0] if 'ld_display' in target.columns else None), 
                                 ("District Type", 'district_type', target['district_type'].iloc[0] if 'district_type' in target.columns else None)]:
        if val and val != "Unknown":
            st.markdown("---")
            st.subheader(f"🏛️ {name} Average: {val}")
            peers = df_merged[df_merged[group_col] == val].copy()
            avg = peers.groupby('fiscal_year').mean(numeric_only=True).reset_index()
            st.dataframe(get_formatted_matrix(add_metrics(avg)), use_container_width=True, hide_index=True)
