import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ School Finance Intelligence")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    res = requests.get(f"{BASE_URL}/{table}?limit=20000", headers=headers)
    return pd.DataFrame(res.json())

# 2. LOAD & MERGE
@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    df_types = fetch_table("district_metadata_mapping") 

    # Dynamic CDS Code Normalization
    for df in [df_sum, df_map, df_types]:
        target_col = 'cds' if 'cds' in df.columns else 'cds_code'
        if target_col in df.columns:
            df.rename(columns={target_col: 'cds_code'}, inplace=True)
            df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

    # Merge
    df = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    
    # Flexible Merge: Only merge columns that exist in the metadata table
    # This prevents the KeyError by checking availability first
    available_metadata = [c for c in ['cds_code', 'district_name', 'district_type'] if c in df_types.columns]
    if 'cds_code' in available_metadata:
        df = df.merge(df_types[available_metadata], on='cds_code', how='left')
    
    if 'county_name' not in df.columns: df['county_name'] = 'Unassigned'
    
    return df

# 3. METRICS
def add_metrics(df):
    potential_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                      'equalized_valuation', 'local_fair_share', 'district_income']
    for col in potential_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Sort and calculate changes
    df = df.sort_values(['district_name', 'fiscal_year'])
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
    available_cols = [c for c in col_order if c in df.columns]
    df_out = df[available_cols].copy()
    rename_map = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid',
                  'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded', 'Pct_Change_Aid': '% Change Actual Aid',
                  'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS',
                  'Pct_Change_Levy': '% Change Actual Levy', 'equalized_valuation': 'Equalized Valuation',
                  'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income'}
    df_out = df_out.rename(columns=rename_map)
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${float(x):,.0f}" if '%' not in col and 'per $100' not in col.lower() else (f"{float(x):.2%}" if '%' in col else (f"{float(x):.4f}" if 'per $100' in col.lower() else f"{float(x):,.0f}")))
    return df_out

# 4. APP EXECUTION
df_merged = add_metrics(get_data())

st.sidebar.header("Filter Settings")
sel_ld = st.sidebar.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().astype(str).tolist()))
sel_type = st.sidebar.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().astype(str).tolist()))
sel_county = st.sidebar.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().astype(str).tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'].astype(str) == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'].astype(str) == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'].astype(str) == sel_county]

sel_district = st.sidebar.selectbox("4️⃣ Select District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().astype(str).tolist()))

page = st.sidebar.radio("Navigation", ["Financial Ledger", "Comparative Analysis", "Revenue Matrix"])

if page == "Financial Ledger":
    st.title("📍 Financial Ledger")
    if sel_district != "Select...":
        st.dataframe(get_formatted_matrix(df_f[df_f['district_name'] == sel_district]), use_container_width=True, hide_index=True)

elif page == "Comparative Analysis":
    st.title("📊 Comparative Averages")
    if sel_district != "Select...":
        target = df_f[df_f['district_name'] == sel_district].iloc[0]
        for name, group_col in [("Legislative District", 'ld_display'), ("District Type", 'district_type')]:
            st.subheader(f"🏛️ {name} Average: {target[group_col]}")
            peers = df_merged[df_merged[group_col] == target[group_col]].groupby('fiscal_year').mean(numeric_only=True).reset_index()
            st.dataframe(get_formatted_matrix(peers), use_container_width=True, hide_index=True)

elif page == "Revenue Matrix":
    st.title("🧮 Revenue Matrix")
    if sel_district != "Select...":
        target_cds = df_f[df_f['district_name'] == sel_district]['cds_code'].iloc[0]
        rev_data = fetch_table(f"revenue?cds_code=eq.{target_cds}")
        if not rev_data.empty:
            matrix = rev_data.pivot_table(index='fiscal_year', columns='line_desc', values='amount', aggfunc='sum')
            st.dataframe(matrix, use_container_width=True)
        else:
            st.info("No revenue data found for this district.")