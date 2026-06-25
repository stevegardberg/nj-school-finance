import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="NJ Finance Dashboard")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_view(view_name):
    res = requests.get(f"{BASE_URL}/{view_name}", headers=headers)
    return pd.DataFrame(res.json())

# 2. LOAD DATA
rev_df = fetch_view("v_unified_revenue")
appr_df = fetch_view("v_unified_appropriations")
types_df = fetch_view("vw_district_cohorts")

# 3. UI FILTERS
st.header("🏛️ Financial Intelligence Explorer")
c1, c2, c3 = st.columns(3)
sel_county = c1.selectbox("County:", ["All"] + sorted(rev_df['county_name'].unique().tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(types_df['district_type'].unique().tolist()))
sel_dist = c3.selectbox("District:", ["Select..."] + sorted(rev_df['district_name'].unique().tolist()))

# 4. DISTRICT LOGIC
if sel_dist != "Select...":
    target_cds = rev_df[rev_df['district_name'] == sel_dist]['cds'].iloc[0]
    st.subheader(f"📍 Ledger: {sel_dist}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Actual Revenues**")
        st.dataframe(rev_df[rev_df['district_name'] == sel_dist], use_container_width=True)
    with col2:
        st.markdown("**Expenditures**")
        st.dataframe(appr_df[appr_df['district_name'] == sel_dist], use_container_width=True)

    # 5. PEER COMPARISON
    st.subheader(f"🏛️ Peer Group Averages")
    peer_cds = types_df[types_df['district_type'] == sel_type]['cds_code']
    peer_appr = appr_df[appr_df['cds'].isin(peer_cds)]
    avg_appr = peer_appr.groupby('category')['amount'].mean().reset_index()
    st.dataframe(avg_appr, use_container_width=True)
