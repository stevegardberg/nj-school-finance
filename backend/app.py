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

# 2. LOAD DATA
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_types = fetch_table("district_metadata_mapping")
    
    # Standardize CDS codes
    for df in [df_sum, df_map, df_types]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merges
    df = df_sum.merge(df_map[['cds_code', 'ld_display', 'county_name']], on='cds_code', how='left')
    df = df.merge(df_types[['cds_code', 'district_type', 'district_name']], on='cds_code', how='left')
    
    # Data Cleaning
    df['district_name'] = df['district_name_y'].fillna(df['district_name_x'])
    df['county_name'] = df['county_name'].fillna('Unassigned')
    df['district_type'] = df['district_type'].fillna('Unknown')
    return df

# 3. METRICS & FORMATTING
def add_metrics(df):
    potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                      'equalized_valuation', 'local_fair_share', 'district_income']
    for col in potential_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df = df.sort_values(['district_name', 'fiscal_year'])
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

def get_formatted_matrix(df):
    rename_map = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid',
                  'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded', 'Pct_Change_Aid': '% Change Actual Aid',
                  'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS',
                  'Pct_Change_Levy': '% Change Actual Levy', 'equalized_valuation': 'Equalized Valuation',
                  'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income'}
    df_out = df[list(rename_map.keys())].copy().rename(columns=rename_map)
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${x:,.0f}" if '%' not in col and 'per $100' not in col.lower() else (f"{x:.2%}" if '%' in col else (f"{x:.4f}" if 'per $100' in col.lower() else f"${x:,.0f}")))
    return df_out

# 4. UI
df_merged = add_metrics(get_data())
st.title("🏛️ New Jersey School Finance Intelligence Platform")

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

page = st.radio("Navigation", ["Financial Ledger", "Revenue Matrix"], horizontal=True)

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    target_cds = target_data['cds_code'].iloc[0]
    
    if page == "Financial Ledger":
        st.subheader(f"📍 Financial Ledger: {sel_district}")
        st.dataframe(get_formatted_matrix(target_data), use_container_width=True, hide_index=True)
    elif page == "Revenue Matrix":
        st.subheader(f"🧮 Revenue Matrix: {sel_district}")
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            pivot = rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum')
            st.dataframe(pivot, use_container_width=True)
        else:
            st.info(f"No revenue data found for CDS {target_cds}.")