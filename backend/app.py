import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. PAGE CONFIG
st.set_page_config(layout="wide")

# Force-clear session on first load
if 'initialized' not in st.session_state:
    st.cache_data.clear()
    st.session_state['initialized'] = True

# 2. DATABASE HANDSHAKE
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
except Exception:
    st.error("🔒 Security credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
}

def fetch_data(url):
    try:
        r = requests.get(f"{url}?limit=1000", headers=headers, timeout=12)
        return r.json() if r.status_code == 200 else []
    except: return []

# 3. DATA PIPELINE
st.markdown("### 🏛️ NJ School Finance Platform")
raw_summary = fetch_data(URLS["summary"])
raw_map = fetch_data(URLS["mapping"])
raw_types = fetch_data(URLS["types"])

# Convert to dataframes with default columns to prevent KeyErrors
df_all = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_map = pd.DataFrame(raw_map) if raw_map else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

# Diagnostic Logs
with st.expander("🔍 Diagnostic Logs", expanded=True):
    st.write(f"Ledger Rows: {len(df_all)} | Metadata Rows: {len(df_types)}")

# Normalization
for df in [df_all, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Merge with safety defaults
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# Force-create columns if merge resulted in missing keys
for col in ["district_name", "district_type", "equalized_valuation", "actual_net_payout", "actual_tax_levy"]:
    if col not in df_joined.columns:
        df_joined[col] = 0.0 if col != "district_name" else "Unknown District"

# 4. FINANCIAL METRICS ENGINE
def add_metrics(df):
    df = df.sort_values("fiscal_year")
    # State Aid % Change
    if "actual_net_payout" in df.columns:
        df["actual_net_payout"] = pd.to_numeric(df["actual_net_payout"], errors='coerce').fillna(0)
        df["state_aid_pct_change"] = df.groupby("cds_code")["actual_net_payout"].pct_change().fillna(0) * 100
    
    # Tax Levy % Change
    if "actual_tax_levy" in df.columns:
        df["actual_tax_levy"] = pd.to_numeric(df["actual_tax_levy"], errors='coerce').fillna(0)
        df["tax_levy_pct_change"] = df.groupby("cds_code")["actual_tax_levy"].pct_change().fillna(0) * 100
    
    # Tax Rate per $100
    if "actual_tax_levy" in df.columns and "equalized_valuation" in df.columns:
        df["equalized_valuation"] = pd.to_numeric(df["equalized_valuation"], errors='coerce').fillna(0)
        df["tax_rate_per_100"] = np.where(df["equalized_valuation"] > 0, (df["actual_tax_levy"] / df["equalized_valuation"]) * 100, 0)
    else:
        df["tax_rate_per_100"] = 0.0
    return df

df_joined = add_metrics(df_joined)

# 5. UI FILTERS & DISPLAY
f1, f2 = st.columns(2)
with f1: 
    sel_dist = st.selectbox("Target District", ["Select..."] + sorted(list(df_joined["district_name"].dropna().unique())))

if sel_dist != "Select...":
    st.markdown(f"#### 📍 Ledger for {sel_dist}")
    st.dataframe(df_joined[df_joined["district_name"] == sel_dist])
else:
    st.info("Select a district to view calculations.")