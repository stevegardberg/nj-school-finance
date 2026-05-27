import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}

@st.cache_data(ttl=3600)
def fetch_all_data(url):
    try:
        res = requests.get(f"{url}?limit=1000", headers=headers)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# 2. LOAD
df_sum = fetch_all_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary")
df_map = fetch_all_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping")

# 3. TRANSFORM
# Ensure summary is clean
df_merged = df_sum.copy()
numeric_cols = ['actual_state_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation']
for col in numeric_cols:
    df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

# Merge mapping if data exists
if not df_map.empty and 'legislative_district' in df_map.columns:
    df_merged = df_merged.merge(df_map[['cds_code', 'legislative_district']], on='cds_code', how='left')
else:
    df_merged['legislative_district'] = "N/A"

# Format LD for clean sorting (Change 3)
df_merged['ld_display'] = df_merged['legislative_district'].apply(lambda x: f"NJ-{int(x):02d}" if pd.notnull(x) and str(x).isdigit() else "Unassigned")

# Calculations (Change 4 & 5)
df_merged = df_merged.sort_values(['district_name', 'fiscal_year'])
df_merged['YoY_State_Aid_Diff'] = df_merged.groupby('district_name')['actual_state_aid'].diff().fillna(0)
df_merged['Tax_Levy_per_100'] = (df_merged['actual_tax_levy'] / df_merged['equalized_valuation'].replace(0, 1)) * 100

# 4. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset All"): st.rerun()

c1, c2 = st.columns(2)
ld_options = sorted([x for x in df_merged['ld_display'].unique() if x != "Unassigned"])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + ld_options)
sel_district = c2.selectbox("2️⃣ District:", ["Select..."] + sorted(df_merged['district_name'].dropna().unique().tolist()))

# 5. MATRIX
if sel_district != "Select...":
    df_render = df_merged[df_merged['district_name'] == sel_district]
    col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 
                 'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']
    st.dataframe(df_render[col_order], use_container_width=True)