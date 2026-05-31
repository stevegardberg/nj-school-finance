import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {
    "apikey": st.secrets["headers"]["apikey"], 
    "Authorization": st.secrets["headers"]["Authorization"],
    "Prefer": "return=representation"
}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    try:
        res = requests.get(f"{BASE_URL}/{table}?limit=10000", headers=headers)
        if res.status_code != 200: return pd.DataFrame()
        data = res.json()
        if isinstance(data, dict): data = [data]
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

# 2. LOAD DATA
df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")
df_map = fetch_table("legislative_mapping")
df_types = fetch_table("vw_district_cohorts")

# 3. STANDARDIZE KEYS
for df in [df_sum, df_enroll, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 4. MERGE
df_merged = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
df_map_clean = df_map.rename(columns={'county_name': 'county_name_map'})
df_merged = df_merged.merge(df_map_clean[['cds_code', 'ld_display', 'county_name_map']], on='cds_code', how='left')
df_merged = df_merged.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

# Resolve county_name collision safely
if 'county_name' not in df_merged.columns:
    df_merged['county_name'] = df_merged.get('county_name_map', 'Unknown')
else:
    df_merged['county_name'] = df_merged['county_name'].combine_first(df_merged.get('county_name_map', pd.Series(dtype=str)))

df_merged.fillna({'county_name': 'Unknown', 'ld_display': 'Unknown', 'district_type': 'Unknown', 'resident_enrollment': 0}, inplace=True)

# 5. CALCULATIONS
def add_metrics(df):
    num_cols = ['actual_state_aid', 'uncapped_aid', 'adequacy_budget', 'actual_tax_levy',
                'equalized_valuation', 'local_fair_share', 'district_income', 'resident_enrollment']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df = df.sort_values(['district_name', 'fiscal_year'])
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

df_merged = add_metrics(df_merged)

# 6. FORMATTING
def get_formatted_matrix(df):
    col_order = ['fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 'Over_Under_Funded',
                 'Pct_Change_Aid', 'local_fair_share', 'actual_tax_levy', 'Over_Under_LFS',
                 'Pct_Change_Levy', 'equalized_valuation', 'Tax_Levy_per_100', 'district_income', 'resident_enrollment']
    available_cols = [c for c in col_order if c in df.columns]
    df_out = df[available_cols].copy()
    rename_map = {'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid',
                  'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded', 'Pct_Change_Aid': '% Change Actual Aid',
                  'local_fair_share': 'Local Fair Share', 'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS',
                  'Pct_Change_Levy': '% Change Actual Levy', 'equalized_valuation': 'Equalized Valuation',
                  'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income', 'resident_enrollment': 'Resident Enrollment'}
    df_out = df_out.rename(columns=rename_map)
    for col in df_out.columns:
        if col != 'Fiscal Year':
            df_out[col] = df_out[col].apply(lambda x: f"${float(x):,.0f}" if '%' not in col and 'per $100' not in col.lower() and 'Enrollment' not in col else (f"{float(x):.2%}" if '%' in col else (f"{float(x):.4f}" if 'per $100' in col.lower() else f"{float(x):,.0f}")))
    return df_out

# 7. UI
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
    target_data = df_f[df_f['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(get_formatted_matrix(target_data), use_container_width=True, hide_index=True)
    ld_val = target_data['ld_display'].iloc[0] if 'ld_display' in target_data.columns else None
    type_val = target_data['district_type'].iloc[0] if 'district_type' in target_data.columns else None
    target_years = target_data['fiscal_year'].unique()
    for name, group_col, val in [("Legislative District", 'ld_display', ld_val), ("District Type", 'district_type', type_val)]:
        if val and val != "Unknown":
            st.markdown("---")
            st.subheader(f"🏛️ {name} Average: {val}")
            peers = df_merged[df_merged[group_col] == val].copy()
            avg = add_metrics(peers).groupby('fiscal_year').mean(numeric_only=True).reset_index()
            avg = avg[avg['fiscal_year'].isin(target_years)]
            st.dataframe(get_formatted_matrix(avg), use_container_width=True, hide_index=True)