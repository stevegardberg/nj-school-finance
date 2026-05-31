import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_raw_data():
    # Fetching raw data ensures we don't miss rows due to SQL View join failures
    aid = pd.DataFrame(requests.get(f"{BASE_URL}/state_aid_summary?select=*", headers=headers).json())
    meta = pd.DataFrame(requests.get(f"{BASE_URL}/district_metadata_mapping?select=*", headers=headers).json())
    
    # Merge in Python to guarantee no rows are dropped
    df = aid.merge(meta[['cds_code', 'district_type']], on='cds_code', how='left')
    return df

df = fetch_raw_data()

# 2. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

# Ensure columns exist and fill missing types
df['district_type'] = df.get('district_type', 'Not Listed').fillna('Not Listed')
df['district_name'] = df.get('district_name', 'Unknown').fillna('Unknown')

# Sidebar Navigation
types = sorted([str(t) for t in df['district_type'].unique()])
sel_type = st.sidebar.selectbox("District Type:", ["All"] + types)

# Filter Logic
df_f = df.copy()
if sel_type != "All":
    df_f = df_f[df_f['district_type'] == sel_type]

# Ensure Boonton is in the list
district_list = sorted([str(d) for d in df_f['district_name'].unique()])
sel_district = st.selectbox("District:", ["Select..."] + district_list)

if sel_district != "Select...":
    st.dataframe(df_f[df_f['district_name'] == sel_district], use_container_width=True)