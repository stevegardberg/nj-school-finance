import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. PAGE CONFIG
st.set_page_config(layout="wide")

if 'initialized' not in st.session_state:
    st.cache_data.clear()
    st.session_state['initialized'] = True

# 2. DATABASE HANDSHAKE & DISCOVERY
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
    SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
    BASE_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1"
    
    # Discovery call
    discovery_res = requests.get(f"{BASE_URL}/", headers=headers, timeout=10)
    available_tables = discovery_res.json() if discovery_res.status_code == 200 else "Could not reach API"
except Exception as e:
    st.error(f"Security/Connection Error: {e}")
    st.stop()

def fetch_data_debug(endpoint):
    url = f"{BASE_URL}/{endpoint}?limit=1000"
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            return r.json(), "Success"
        else:
            return [], f"Error {r.status_code}"
    except Exception as e:
        return [], str(e)

# 3. DATA ACQUISITION
st.markdown("### 🏛️ NJ School Finance Platform")

# Fetching Data
raw_summary, s_msg = fetch_data_debug("state_aid_summary")
raw_map, m_msg = fetch_data_debug("legislative_mapping")
raw_types, t_msg = fetch_data_debug("district_metadata_mapping")

# Visual Diagnostic
with st.expander("🔍 Diagnostic & Table Discovery", expanded=True):
    st.write(f"Summary: {len(raw_summary)} rows | Status: {s_msg}")
    st.write(f"Mapping: {len(raw_map)} rows | Status: {m_msg}")
    st.write(f"Metadata (Types): {len(raw_types)} rows | Status: {t_msg}")
    st.write("Available Tables/Views:", available_tables)

# 4. DATAFRAME PROCESSING
df_all = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

# Normalize IDs
for df in [df_all, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Merge with safety
df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# Force-create columns so app doesn't crash
for col in ["district_name", "actual_net_payout", "actual_tax_levy", "equalized_valuation"]:
    if col not in df_joined.columns:
        df_joined[col] = 0.0 if col != "district_name" else "Unknown District"

# 5. FINANCIAL METRICS ENGINE
df_joined = df_joined.sort_values("fiscal_year")
df_joined["actual_net_payout"] = pd.to_numeric(df_joined["actual_net_payout"], errors='coerce').fillna(0)
df_joined["actual_tax_levy"] = pd.to_numeric(df_joined["actual_tax_levy"], errors='coerce').fillna(0)
df_joined["equalized_valuation"] = pd.to_numeric(df_joined["equalized_valuation"], errors='coerce').fillna(0)

# YoY % Changes
df_joined["state_aid_pct_change"] = df_joined.groupby("cds_code")["actual_net_payout"].pct_change().fillna(0) * 100
df_joined["tax_levy_pct_change"] = df_joined.groupby("cds_code")["actual_tax_levy"].pct_change().fillna(0) * 100

# Tax Rate per $100
df_joined["tax_rate_per_100"] = np.where(df_joined["equalized_valuation"] > 0, 
                                        (df_joined["actual_tax_levy"] / df_joined["equalized_valuation"]) * 100, 0)

# 6. UI FILTERS & DISPLAY
f1, f2 = st.columns(2)
with f1: 
    sel_dist = st.selectbox("Target District", ["Select..."] + sorted(list(df_joined["district_name"].dropna().unique())))

if sel_dist != "Select...":
    st.markdown(f"#### 📍 Ledger for {sel_dist}")
    display_df = df_joined[df_joined["district_name"] == sel_dist].copy()
    st.dataframe(display_df)
else:
    st.info("Select a district to view calculations.")