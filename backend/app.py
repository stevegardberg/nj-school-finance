import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}

@st.cache_data(ttl=3600)
def fetch_all_data(url):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{url}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD DATA
df_summary = fetch_all_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary")
df_map = fetch_all_data("https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping")

# 3. TRANSFORM & MERGE
# Ensure cds_code alignment
df_summary['cds_code'] = df_summary['cds_code'].astype(str).str.zfill(6)
df_map['cds_code'] = df_map['cds_code'].astype(str).str.zfill(6)

# Merge Mapping
df_merged = df_summary.merge(df_map[['cds_code', 'legislative_district']], on='cds_code', how='left')

# Data Cleanup
numeric_cols = ['actual_state_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation']
for col in numeric_cols:
    df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

df_merged = df_merged.sort_values(['district_name', 'fiscal_year'])

# 4. CALCULATIONS
# Change 4: YoY State Aid Difference
df_merged['YoY_State_Aid_Diff'] = df_merged.groupby('district_name')['actual_state_aid'].diff().fillna(0)
# Change 5: Tax Levy per $100
df_merged['Tax_Levy_per_100'] = (df_merged['actual_tax_levy'] / df_merged['equalized_valuation'].replace(0, 1)) * 100

# 5. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset"): st.rerun()

districts = sorted([d for d in df_merged['district_name'].unique() if isinstance(d, str)])
sel_district = st.selectbox("Select District:", ["Select..."] + districts)

# 6. DISPLAY
if sel_district != "Select...":
    df_render = df_merged[df_merged['district_name'] == sel_district]
    # Final Column Order
    col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 
                 'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']
    
    st.markdown(f"#### 📍 Ledger: {sel_district}")
    st.dataframe(df_render[col_order], use_container_width=True)