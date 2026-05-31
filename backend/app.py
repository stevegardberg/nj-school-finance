import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_data():
    # Fetch from the View we just created
    url = f"{BASE_URL}/v_district_finance_intelligence?select=*"
    res = requests.get(url, headers=headers)
    return pd.DataFrame(res.json())

# 2. LOAD
df = fetch_data()

# 3. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

# Get types directly from the pre-joined view
types = sorted([t for t in df['district_type'].dropna().unique().tolist() if t != "Not Listed"])

sel_type = st.sidebar.selectbox("District Type:", ["All"] + types)
if sel_type != "All":
    df = df[df['district_type'] == sel_type]

sel_district = st.selectbox("District:", ["Select..."] + sorted(df['district_name'].unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df[df['district_name'] == sel_district], use_container_width=True)