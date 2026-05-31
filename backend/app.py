import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_data():
    url = f"{BASE_URL}/v_district_finance_intelligence?select=*"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        st.error(f"Error fetching data: {res.status_code}")
        return pd.DataFrame()
    return pd.DataFrame(res.json())

df = fetch_data()

# 2. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

if not df.empty:
    # Ensure columns exist safely
    df['district_type'] = df.get('district_type', 'Not Listed').fillna('Not Listed')
    df['district_name'] = df.get('district_name', 'Unknown').fillna('Unknown')

    # Sidebar Filter
    types = sorted([str(t) for t in df['district_type'].unique() if t != "Not Listed"])
    sel_type = st.sidebar.selectbox("District Type:", ["All"] + types)
    
    if sel_type != "All":
        df_f = df[df['district_type'] == sel_type]
    else:
        df_f = df

    # Safe Sorting Fix
    district_list = sorted([str(d) for d in df_f['district_name'].unique()])
    sel_district = st.selectbox("District:", ["Select..."] + district_list)

    if sel_district != "Select...":
        st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)
else:
    st.warning("No data found. Please check your SQL View configuration in Supabase.")