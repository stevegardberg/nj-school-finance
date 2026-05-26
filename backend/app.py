import streamlit as st
import pandas as pd
import numpy as np
import requests

# Set page configuration
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. LIVE SECURE DATABASE HANDSHAKE
# -----------------------------------------------------------------------------
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
except Exception:
    st.error("🔒 Security handshake credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "Summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "Mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "Types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping",
    "Revenue": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/revenue"
}

def fetch_supabase_table_data(url):
    all_records = []
    page = 0
    page_size = 1000
    try:
        while True:
            offset = page * page_size
            target = f"{url}?limit={page_size}&offset={offset}"
            response = requests.get(target, headers=headers, timeout=12)
            if response.status_code == 200:
                data = response.json()
                if not data: break
                all_records.extend(data)
                page += 1
            else: break
        return all_records
    except: return []

# -----------------------------------------------------------------------------
# 2. DATA PIPELINE WITH DIAGNOSTICS
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ NJ School Finance Intelligence")
data_frames = {}
for name, url in URLS.items():
    raw = fetch_supabase_table_data(url)
    if not raw:
        st.warning(f"⚠️ {name} table returned no data.")
        data_frames[name] = pd.DataFrame()
    else:
        data_frames[name] = pd.DataFrame(raw)

# Normalize CDS codes
def clean_cds(val):
    return str(val).split('.')[0].strip().zfill(6)[:6]

df_sum = data_frames["Summary"]
if not df_sum.empty: df_sum["join_key"] = df_sum["cds_code"].apply(clean_cds)

# -----------------------------------------------------------------------------
# 3. RELATIONAL JOIN & PURGE
# -----------------------------------------------------------------------------
# Standardizing joins
df_types = data_frames["Types"]
if not df_types.empty:
    df_types["join_key"] = df_types["cds_code"].apply(clean_cds)
    df_types.rename(columns={"district_name": "d_name", "district_type": "d_type"}, inplace=True)
else:
    df_types = pd.DataFrame(columns=["join_key", "d_name", "d_type"])

df_joined = pd.merge(df_sum, df_types[["join_key", "d_name", "d_type"]], on="join_key", how="left")
df_joined["d_name"] = df_joined["d_name"].fillna("Unknown District")

# -----------------------------------------------------------------------------
# 4. FILTERS & UI
# -----------------------------------------------------------------------------
f1, f2, f4 = st.columns(3)
with f1: sel_type = st.selectbox("District Type:", ["All"] + sorted(df_joined["d_type"].dropna().unique().tolist()))
with f4: sel_dist = st.selectbox("Target District:", ["Select..."] + sorted(df_joined["d_name"].dropna().unique().tolist()))

# Filter logic
df_cascade = df_joined.copy()
if sel_type != "All": df_cascade = df_cascade[df_cascade["d_type"] == sel_type]

tab1, tab2, tab3 = st.tabs(["⚖️ VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return"])

with tab1:
    if sel_dist != "Select...":
        st.dataframe(df_cascade[df_cascade["d_name"] == sel_dist], use_container_width=True)
    else:
        st.info("Select a district to begin.")