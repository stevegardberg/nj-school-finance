import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_view():
    # We only fetch the view. The database did all the heavy lifting.
    res = requests.get(f"{BASE_URL}/v_finance_dashboard?select=*", headers=headers)
    return pd.DataFrame(res.json())

df = fetch_view()

# UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

if not df.empty:
    types = sorted([str(t) for t in df['district_type'].fillna("Not Listed").unique()])
    sel_type = st.sidebar.selectbox("District Type:", ["All"] + types)
    
    if sel_type != "All":
        df = df[df['district_type'].fillna("Not Listed") == sel_type]
        
    districts = sorted([str(d) for d in df['district_name'].unique()])
    sel_district = st.selectbox("District:", ["Select..."] + districts)

    if sel_district != "Select...":
        st.dataframe(df[df['district_name'] == sel_district], use_container_width=True)