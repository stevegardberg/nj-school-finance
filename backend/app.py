import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=60)
def fetch_table(table):
    url = f"{BASE_URL}/{table}?select=*"
    res = requests.get(url, headers=headers)
    
    if res.status_code != 200:
        st.error(f"API Error {res.status_code} on {table}: {res.text}")
        return pd.DataFrame()
    
    data = res.json()
    if not data:
        st.warning(f"Table '{table}' returned an empty list [].")
        return pd.DataFrame()
        
    df = pd.DataFrame(data)
    df.columns = [c.lower().strip() for c in df.columns]
    return df

# Fetch and check
df_enroll = fetch_table("v_aggregated_enrollment")

if df_enroll.empty:
    st.error("v_aggregated_enrollment is empty. Check if the view exists and has permissions.")
    st.stop()

st.success("Table loaded successfully!")
st.dataframe(df_enroll.head())