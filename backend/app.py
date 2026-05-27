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
df_types = fetch_table("vw_district_cohorts")

df_sum["cds_code"] = df_sum["cds_code"].astype(str).str.zfill(6)
df_map["cds_code"] = df_map["cds_code"].astype(str).str.zfill(6)
df_types["cds_code"] = df_types["cds_code"].astype(str).str.zfill(6)

df_merged = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# 3. CALCULATIONS
numeric_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation', 'local_fair_share', 'district_income']
for col in numeric_cols:
    df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

# Robust Metric Addition
def add_metrics(df):
    # Only sort if columns exist
    if 'district_name' in df.columns and 'fiscal_year' in df.columns:
        df = df.sort_values(['district_name', 'fiscal_year'])
        df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
        df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    else:
        df['Pct_Change_Aid'] = 0
        df['Pct_Change_Levy'] = 0
        
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

df_merged = add_metrics(df_merged)

# 4. FORMATTING
def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 'Over_Under_Funded', 'Pct_Change_Aid', 'local_fair_share', 'actual_tax_levy', 'Over_Under_LFS', 'Pct_Change_Levy', 'equalized_valuation', 'Tax_Levy_per_100', 'district_income']
    rename_map = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid', 'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded', 'Pct_Change_Aid': '% Change Actual Aid', 'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS', 'Pct_Change_Levy': '% Change Actual Levy', 'equalized_valuation': 'Equalized Valuation', 'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income'}
    
    available_cols = [c for c in col_order if c in df.columns]
    df_out = df[available_cols].copy().rename(columns=rename_map)
    
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${float(x):,.0f}" if '%' not in col and 'per $100' not in col.lower() else (f"{float(x):.2%}" if '%' in col else f"{float(x):.4f}"))
    return df_out

# 5. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset"): st.rerun()

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
    st.dataframe(get_formatted_matrix(df_f[df_f['district_name'] == sel_district]), use_container_width=True, hide_index=True)

    target_data = df_merged[df_merged['district_name'] == sel_district]
    target_years = target_data['fiscal_year'].unique()
    ld_val = target_data['ld_display'].iloc[0]
    type_val = target_data['district_type'].iloc[0]

    st.markdown("---")
    for name, group_col, val in [("Legislative District", 'ld_display', ld_val), ("District Type", 'district_type', type_val)]:
        st.subheader(f"🏛️ {name} Average: {val}")
        peers = df_merged[(df_merged[group_col] == val) & (df_merged['fiscal_year'].isin(target_years))]
        avg = peers.groupby('fiscal_year')[numeric_cols].mean().reset_index()
        st.dataframe(get_formatted_matrix(add_metrics(avg)), use_container_width=True, hide_index=True)