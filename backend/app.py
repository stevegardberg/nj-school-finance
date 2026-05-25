import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. PAGE CONFIG
st.set_page_config(layout="wide")

if 'initialized' not in st.session_state:
    st.cache_data.clear()
    st.session_state['initialized'] = True

# 2. DATABASE HANDSHAKE
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
except:
    st.error("🔒 Security credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
}

def fetch_data_debug(url):
    try:
        r = requests.get(f"{url}?limit=1000", headers=headers, timeout=12)
        if r.status_code == 200:
            return r.json(), "Success"
        else:
            return [], f"Error {r.status_code}: {r.text}"
    except Exception as e:
        return [], str(e)

# 3. DATA PIPELINE
st.markdown("### 🏛️ NJ School Finance Platform")
raw_summary, s_msg = fetch_data_debug(URLS["summary"])
raw_map, m_msg = fetch_data_debug(URLS["mapping"])
raw_types, t_msg = fetch_data_debug(URLS["types"])

# Diagnostic Logs with Error Reporting
with st.expander("🔍 Diagnostic Logs", expanded=True):
    st.write(f"Summary: {len(raw_summary)} rows | Status: {s_msg}")
    st.write(f"Mapping: {len(raw_map)} rows | Status: {m_msg}")
    st.write(f"Metadata (Types): {len(raw_types)} rows | Status: {t_msg}")

df_all = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

# Normalization
for df in [df_all, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Merge
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# Force-create columns
for col in ["district_name", "district_type"]:
    if col not in df_joined.columns:
        df_joined[col] = "Unknown"

# 4. METRICS
def add_metrics(df):
    if "actual_net_payout" in df.columns:
        df["actual_net_payout"] = pd.to_numeric(df["actual_net_payout"], errors='coerce').fillna(0)
    return df

df_joined = add_metrics(df_joined)

# 5. UI
f1, f2 = st.columns(2)
with f1: 
    sel_dist = st.selectbox("Target District", ["Select..."] + sorted(list(df_joined["district_name"].dropna().unique())))

if sel_dist != "Select...":
    st.dataframe(df_joined[df_joined["district_name"] == sel_dist])
else:
    st.info("Select a district to view calculations.")