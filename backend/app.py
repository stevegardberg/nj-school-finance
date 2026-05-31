import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# ... (rest of your fetch/merge logic from previous steps) ...

# 3. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

# FORCE UNIQUE LIST
# We convert to string and drop nulls to guarantee valid options for the dropdown
districts = df_merged['district_name'].dropna().astype(str).unique()
districts = sorted([d for d in districts if d and d.lower() != 'nan'])

if len(districts) == 0:
    st.error("No district names found in the data.")
else:
    sel_district = st.selectbox("Select District:", ["Select..."] + districts)

    if sel_district != "Select...":
        target = df_merged[df_merged['district_name'].astype(str) == sel_district]
        st.dataframe(target, use_container_width=True)