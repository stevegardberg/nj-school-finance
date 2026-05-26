import streamlit as st
import pandas as pd
import requests

st.set_page_config(layout="wide")

# 1. HANDSHAKE
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
    SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(table):
    url = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/{table}?limit=5000"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA LOAD
st.title("🏛️ NJ School Finance Intelligence")
# Fetching tables
df_sum = pd.DataFrame(fetch("state_aid_summary"))
df_types = pd.DataFrame(fetch("district_metadata_mapping"))

# DIAGNOSTICS: Show us exactly what we have
with st.expander("🔍 System Status (Click to see why data is missing)"):
    st.write(f"Summary rows loaded: {len(df_sum)}")
    st.write(f"Metadata rows loaded: {len(df_types)}")
    if not df_types.empty:
        st.write("Columns found in Metadata:", df_types.columns.tolist())

# 3. MAPPING (Only if data exists)
if not df_sum.empty and not df_types.empty:
    # Ensure CDS codes match formats
    df_sum['cds_code'] = df_sum['cds_code'].astype(str).str.zfill(6)
    df_types['cds_code'] = df_types['cds_code'].astype(str).str.zfill(6)
    df_all = pd.merge(df_sum, df_types, on='cds_code', how='left')
else:
    df_all = df_sum

# 4. FILTERS (Safe fallbacks)
cols = st.columns(2)
# Use 'district_name' if it exists, otherwise use 'cds_code'
name_col = 'district_name' if 'district_name' in df_all.columns else 'cds_code'
districts = sorted(df_all[name_col].dropna().unique().tolist()) if name_col in df_all.columns else []

with cols[0]:
    sel_dist = st.selectbox("Target District:", ["Select..."] + districts)

# 5. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return"])
with tab1:
    if sel_dist != "Select...":
        st.dataframe(df_all[df_all[name_col] == sel_dist], use_container_width=True)
    else:
        st.info("Select a district.")