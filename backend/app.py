import streamlit as st
import pandas as pd
import requests

st.set_page_config(layout="wide")

# 1. HANDSHAKE
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
    BASE_URL = f"https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(table):
    url = f"{BASE_URL}/{table}?limit=5000"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA LOAD
st.title("🏛️ NJ School Finance Intelligence")
df_sum = pd.DataFrame(fetch("state_aid_summary"))

# RECOVERY MODE: Use CDS_CODE if district_name is missing
if not df_sum.empty:
    df_sum['cds_code'] = df_sum['cds_code'].astype(str).str.zfill(6)
    display_col = 'district_name' if 'district_name' in df_sum.columns else 'cds_code'
else:
    df_sum = pd.DataFrame()
    display_col = 'cds_code'

# 3. UI
with st.expander("🔍 System Status", expanded=True):
    st.write(f"Summary rows: {len(df_sum)}")
    st.write("Metadata table is empty. Filters will be limited to CDS Codes.")

if not df_sum.empty:
    districts = sorted(df_sum[display_col].dropna().unique().tolist())
    sel_dist = st.selectbox("Target District (or CDS Code):", ["Select..."] + districts)

    if sel_dist != "Select...":
        st.dataframe(df_sum[df_sum[display_col] == sel_dist], use_container_width=True)
    else:
        st.info("Select a district.")
else:
    st.error("No data available.")