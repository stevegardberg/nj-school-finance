import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

# --- 1. SETUP & HANDSHAKE ---
if 'initialized' not in st.session_state:
    st.cache_data.clear()
    st.session_state['initialized'] = True

try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
except:
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

# --- 2. DATA PIPELINE ---
st.markdown("### 🏛️ NJ School Finance Platform")
raw_summary, raw_map, raw_types = fetch_data(URLS["summary"]), fetch_data(URLS["mapping"]), fetch_data(URLS["types"])

df_all = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_map = pd.DataFrame(raw_map) if raw_map else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

# Normalization
for df in [df_all, df_map, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Merge & Metrics
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# Financial Metrics Engine
def add_metrics(df):
    df = df.sort_values("fiscal_year")
    for col in ["actual_net_payout", "actual_tax_levy"]:
        if col in df.columns:
            df[f"{col}_pct_change"] = df.groupby("cds_code")[col].pct_change().fillna(0) * 100
    if "actual_tax_levy" in df.columns and "equalized_valuation" in df.columns:
        df["tax_rate_per_100"] = np.where(df["equalized_valuation"] > 0, (df["actual_tax_levy"] / df["equalized_valuation"]) * 100, 0)
    return df

df_joined = add_metrics(df_joined)

# --- 3. UI FILTERS ---
with st.expander("🔍 Diagnostic Logs", expanded=True):
    st.write(f"Ledger Rows: {len(df_joined)} | Metadata Rows: {len(df_types)}")

f1, f2 = st.columns(2)
with f1: sel_dist = st.selectbox("Target District", ["Select..."] + sorted(list(df_joined["district_name"].dropna().unique())))

# --- 4. DISPLAY ---
if sel_dist != "Select...":
    st.markdown(f"#### 📍 Ledger for {sel_dist}")
    st.dataframe(df_joined[df_joined["district_name"] == sel_dist])
else:
    st.info("Select a district to view calculations.")