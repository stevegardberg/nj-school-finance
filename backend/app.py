import streamlit as st
import requests
import pandas as pd

# Set page layout
st.set_page_config(layout="wide")

# 1. SETUP
# Ensure your Streamlit secrets are configured with 'apikey' and 'Authorization'
headers = {
    "apikey": st.secrets["headers"]["apikey"], 
    "Authorization": st.secrets["headers"]["Authorization"],
    "Prefer": "return=representation"
}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

# 2. DATA FETCHING WITH PAGINATION
@st.cache_data(ttl=300)
def fetch_view():
    all_data = []
    page = 0
    while True:
        # Fetch 1000 records at a time from the SQL View
        url = f"{BASE_URL}/v_finance_dashboard?select=*&limit=1000&offset={page * 1000}"
        res = requests.get(url, headers=headers)
        
        if res.status_code != 200:
            break
            
        data = res.json()
        if not data:
            break
            
        all_data.extend(data)
        page += 1
    
    return pd.DataFrame(all_data)

# Load data
df = fetch_view()

# 3. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

if not df.empty:
    # Ensure column existence and data cleaning
    df['district_type'] = df.get('district_type', 'Not Listed').fillna('Not Listed')
    df['district_name'] = df.get('district_name', 'Unknown').fillna('Unknown')

    # Sidebar Filter
    types = sorted([str(t) for t in df['district_type'].unique()])
    sel_type = st.sidebar.selectbox("District Type:", ["All"] + types)
    
    # Apply type filter
    if sel_type != "All":
        df_f = df[df['district_type'] == sel_type]
    else:
        df_f = df

    # District Selection
    # Sorting ensures names appear alphabetically
    district_list = sorted([str(d) for d in df_f['district_name'].unique()])
    sel_district = st.selectbox("District:", ["Select..."] + district_list)

    # Display Data
    if sel_district != "Select...":
        result = df_f[df_f['district_name'] == sel_district]
        st.dataframe(result, use_container_width=True)
else:
    st.warning("No data found. Please check your Supabase connection and View configuration.")

# Debug info (optional - remove once verified)
st.sidebar.write(f"Total rows loaded: {len(df)}")