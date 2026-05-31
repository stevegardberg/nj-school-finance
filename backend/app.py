import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    res = requests.get(f"{BASE_URL}/{table}?limit=1000", headers=headers)
    df = pd.DataFrame(res.json())
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

st.title("DEBUG: Column & Key Inspector")

df_sum = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_aggregated_enrollment")

st.write("---")
st.write("### df_sum columns:", df_sum.columns.tolist())
st.write("### df_enroll columns:", df_enroll.columns.tolist())

# Test key existence
sum_keys = ['cds_code', 'fiscal_year']
enroll_keys = ['cds_code', 'fiscal_year']

missing_sum = [k for k in sum_keys if k not in df_sum.columns]
missing_enroll = [k for k in enroll_keys if k not in df_enroll.columns]

if missing_sum:
    st.error(f"df_sum is missing: {missing_sum}")
if missing_enroll:
    st.error(f"df_enroll is missing: {missing_enroll}")

if not missing_sum and not missing_enroll:
    st.success("Both DataFrames have the required merge keys. Attempting sample merge...")
    try:
        sample = df_sum.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
        st.write("Merge successful! Sample rows:")
        st.dataframe(sample.head())
    except Exception as e:
        st.error(f"Merge failed: {e}")