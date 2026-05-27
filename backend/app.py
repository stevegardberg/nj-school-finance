import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔍 Data Integrity Diagnostic")

# 1. AUTH
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}

# 2. FETCH AND INSPECT
urls = {
    "Summary": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/state_aid_summary",
    "Mapping": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/legislative_mapping",
    "Types": "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/district_metadata_mapping"
}

for name, url in urls.items():
    st.subheader(f"Table: {name}")
    try:
        res = requests.get(f"{url}?limit=10", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                st.write(f"✅ Success. Rows: {len(data)}")
                st.write("Columns found:", list(df.columns))
                st.dataframe(df.head(3))
            else:
                st.warning("⚠️ Table returned 0 rows.")
        else:
            st.error(f"❌ API Error {res.status_code}: {res.text}")
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")