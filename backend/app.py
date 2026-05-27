import streamlit as st
import pandas as pd
import requests

st.set_page_config(layout="wide")

# 1. SETUP & FETCH
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
URLS = {
    "Summary": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary",
    "Types": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/district_metadata_mapping"
}

@st.cache_data(ttl=3600)
def fetch_all_data(url):
    res = requests.get(url, headers=headers)
    return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()

df_summary = fetch_all_data(URLS["Summary"])
df_types = fetch_all_data(URLS["Types"])

# 2. DATA PROCESSING & CALCULATIONS
if not df_summary.empty:
    df_summary = df_summary.sort_values(['district_name', 'fiscal_year'])
    # Ensure numeric for calculations
    for col in ['actual_state_aid', 'adequacy_budget', 'actual_tax_levy', 'equalized_valuation']:
        df_summary[col] = pd.to_numeric(df_summary[col], errors='coerce').fillna(0)
    
    # Change 4: YoY Delta
    df_summary['YoY_State_Aid_Diff'] = df_summary.groupby('district_name')['actual_state_aid'].diff().fillna(0)
    # Change 5: Tax Levy per $100
    df_summary['Tax_Levy_per_100'] = (df_summary['actual_tax_levy'] / df_summary['equalized_valuation'].replace(0, 1)) * 100

# 3. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

# Fix: Clean district list to ensure strings only
valid_districts = sorted([d for d in df_summary['district_name'].unique().tolist() if isinstance(d, str)])
sel_district = st.selectbox("Target District:", ["Select..."] + valid_districts)

# 4. DISPLAY
if sel_district != "Select...":
    df_render = df_summary[df_summary['district_name'] == sel_district]
    
    # Define Column Order (Change 4 & 5 included)
    col_order = ['fiscal_year', 'actual_state_aid', 'YoY_State_Aid_Diff', 'adequacy_budget', 
                 'actual_tax_levy', 'equalized_valuation', 'Tax_Levy_per_100']
    
    st.markdown(f"#### 📍 Ledger: {sel_district}")
    st.dataframe(df_render[col_order], use_container_width=True)

    # Peer Group Analysis (Nested beneath ledger)
    st.markdown("#### 📊 Peer Group Analysis")
    if not df_types.empty:
        peer_data = df_types[df_types['district_name'] == sel_district]
        st.dataframe(peer_data, use_container_width=True)
    else:
        st.info("No peer group metadata available for this district.")