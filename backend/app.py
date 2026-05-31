import streamlit as st
import requests
import pandas as pd
from rapidfuzz import process, fuzz

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?select=*&limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD & PREPARE
df_aid = fetch_table("state_aid_summary")
df_meta = fetch_table("district_metadata_mapping")

# Function to perform Fuzzy Matching
def fuzzy_merge(left_df, right_df, left_col, right_col, threshold=90):
    # Get unique names from the mapping table
    right_names = right_df[right_col].unique()
    
    def get_best_match(name):
        match = process.extractOne(name, right_names, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= threshold:
            return match[0]
        return None
    
    left_df['match_key'] = left_df[left_col].apply(get_best_match)
    return left_df.merge(right_df, left_on='match_key', right_on=right_col, how='left')

# Apply Fuzzy Match
df_aid = fuzzy_merge(df_aid, df_meta, 'district_name', 'district_name')

# 3. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")
st.sidebar.write("Unique Types found:", sorted(df_aid['district_type'].dropna().unique().tolist()))

c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_aid.get('ld_display', pd.Series(['Unknown'])).unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_aid['district_type'].fillna('Not Listed').unique().tolist()))
sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_aid['district_name'].unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_aid[df_aid['district_name'] == sel_district], use_container_width=True)