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
    df_types = fetch_table("vw_district_cohorts")

    for df in [df_sum, df_map, df_types]:
        col = 'cds' if 'cds' in df.columns else 'cds_code'
        if col in df.columns:
            df.rename(columns={col: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    
    df = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    df = df.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')
    return df

def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                      'equalized_valuation', 'local_fair_share', 'district_income']
    for col in potential_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 'Over_Under_Funded',
                 'local_fair_share', 'actual_tax_levy', 'Over_Under_LFS', 'equalized_valuation', 'Tax_Levy_per_100', 'district_income']
    available_cols = [c for c in col_order if c in df.columns]
    df_out = df[available_cols].copy()
    rename_map = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid',
                  'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded',
                  'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS',
                  'equalized_valuation': 'Equalized Valuation', 'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income'}
    df_out = df_out.rename(columns=rename_map)
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${float(x):,.0f}" if '%' not in col and 'per $100' not in col.lower() else (f"{float(x):.4f}" if 'per $100' in col.lower() else f"${float(x):,.0f}"))
    return df_out

# UI
df_merged = add_metrics(get_data())

st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
page = st.sidebar.radio("Navigation", ["Financial Ledger", "Revenue Matrix"])
c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna('Unassigned').unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    
    if page == "Financial Ledger":
        st.subheader(f"📍 Financial Ledger: {sel_district}")
        st.dataframe(get_formatted_matrix(target_data), use_container_width=True)
        
        # Comparative Averages
        st.markdown("---")
        for name, col in [("Legislative District", 'ld_display'), ("District Type", 'district_type')]:
            val = target_data[col].iloc[0]
            st.subheader(f"🏛️ {name} Average: {val}")
            peers = df_merged[df_merged[col] == val].groupby('fiscal_year').mean(numeric_only=True).reset_index()
            st.dataframe(get_formatted_matrix(peers), use_container_width=True)

    elif page == "Revenue Matrix":
        target_cds = target_data['cds_code'].iloc[0]
        # DEBUG: Fetch first 5 rows of revenue to check column names
        st.write(f"Querying revenue for CDS: {target_cds}")
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            st.dataframe(rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum'), use_container_width=True)
        else:
            st.info("No data found. Check if table uses 'cds' instead of 'cds_code'.")
            sample = fetch_table("revenue?limit=5")
            st.write("Table sample columns:", sample.columns.tolist())