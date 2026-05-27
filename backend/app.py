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

# 2. DATA LOAD & MERGE
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

df_merged = df_merged.sort_values(['district_name', 'fiscal_year'])
df_merged['Over_Under_Funded'] = df_merged['actual_state_aid'] - df_merged['uncapped_aid']
df_merged['Pct_Change_Aid'] = df_merged.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
df_merged['Over_Under_LFS'] = df_merged['actual_tax_levy'] - df_merged['local_fair_share']
df_merged['Pct_Change_Levy'] = df_merged.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
df_merged['Tax_Levy_per_100'] = (df_merged['actual_tax_levy'] / df_merged['equalized_valuation'].replace(0, 1)) * 100

# 4. FORMATTING FUNCTION (WITH ERROR HANDLING)
def get_formatted_matrix(df):
    col_order = [
        'fiscal_year', 'adequacy_budget', 'uncapped_aid', 'actual_state_aid', 
        'Over_Under_Funded', 'Pct_Change_Aid', 'local_fair_share', 'actual_tax_levy', 
        'Over_Under_LFS', 'Pct_Change_Levy', 'equalized_valuation', 
        'Tax_Levy_per_100', 'district_income'
    ]
    rename_map = {
        'fiscal_year': 'Fiscal Year', 'adequacy_budget': 'Adequacy Budget', 'uncapped_aid': 'Uncapped Aid',
        'actual_state_aid': 'Actual Aid', 'Over_Under_Funded': 'Over/Under Funded', 
        'Pct_Change_Aid': '% Change Actual Aid', 'local_fair_share': 'Local Fair Share', 
        'actual_tax_levy': 'Actual Levy', 'Over_Under_LFS': 'Over/Under LFS', 
        'Pct_Change_Levy': '% Change Actual Levy', 'equalized_valuation': 'Equalized Valuation', 
        'Tax_Levy_per_100': 'Levy per $100', 'district_income': 'District Income'
    }
    df_out = df[col_order].rename(columns=rename_map)
    
    for col in df_out.columns:
        def safe_format(val, cname):
            try:
                v = float(str(val).replace('$', '').replace(',', ''))
                if cname in ['% Change Actual Aid', '% Change Actual Levy']: return f"{v:.2%}"
                if cname == 'Levy per $100': return f"{v:.4f}"
                return f"${v:,.0f}"
            except: return str(val)
        df_out[col] = df_out[col].apply(lambda x: safe_format(x, col))
    return df_out

# 5. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset"): st.rerun()

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].fillna("Unassigned").unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].fillna("Unassigned").unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].fillna("Unassigned").unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

if sel_district != "Select...":
    st.markdown(f"#### 📍 Ledger: {sel_district}")
    st.dataframe(get_formatted_matrix(df_f[df_f['district_name'] == sel_district]), use_container_width=True, hide_index=True)