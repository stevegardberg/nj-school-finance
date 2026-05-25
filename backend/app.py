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
    SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
    BASE_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1"
except Exception as e:
    st.error(f"Security/Connection Error: {e}")
    st.stop()

def fetch_data_debug(endpoint):
    url = f"{BASE_URL}/{endpoint}?limit=2000" # Increased limit to capture full scope
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

raw_summary, s_msg = fetch_data_debug("state_aid_summary")
raw_map, m_msg = fetch_data_debug("legislative_mapping")
raw_types, t_msg = fetch_data_debug("vw_district_cohorts") 

with st.expander("🔍 Diagnostic Logs", expanded=False):
    st.write(f"Summary: {len(raw_summary)} rows | Status: {s_msg}")
    st.write(f"Mapping: {len(raw_map)} rows | Status: {m_msg}")
    st.write(f"Metadata (vw_district_cohorts): {len(raw_types)} rows | Status: {t_msg}")

# 4. DATAFRAME PROCESSING
df_all = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

for df in [df_all, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

df_joined = pd.merge(df_all, df_types, on="cds_code", how="left")

# Force-fill missing names
df_joined["district_name"] = df_joined["district_name"].fillna("Unknown District")

# 5. FINANCIAL METRICS ENGINE
df_joined = df_joined.sort_values("fiscal_year")
# Ensure numeric conversion
cols_to_num = ["actual_net_payout", "actual_tax_levy", "equalized_valuation"]
for col in cols_to_num:
    df_joined[col] = pd.to_numeric(df_joined[col], errors='coerce').fillna(0)

# Metrics
df_joined["state_aid_pct_change"] = df_joined.groupby("cds_code")["actual_net_payout"].pct_change().fillna(0) * 100
df_joined["tax_levy_pct_change"] = df_joined.groupby("cds_code")["actual_tax_levy"].pct_change().fillna(0) * 100
df_joined["tax_rate_per_100"] = np.where(df_joined["equalized_valuation"] > 0, 
                                        (df_joined["actual_tax_levy"] / df_joined["equalized_valuation"]) * 100, 0)

# 6. UI FILTERS & DISPLAY
districts = sorted(df_joined["district_name"].unique())
sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + districts)

if sel_dist != "Select a District...":
    st.markdown(f"#### 📍 Ledger for {sel_dist}")
    display_df = df_joined[df_joined["district_name"] == sel_dist].copy()
    # Format columns for display
    st.dataframe(display_df.style.format({
        "state_aid_pct_change": "{:.2f}%",
        "tax_levy_pct_change": "{:.2f}%",
        "tax_rate_per_100": "${:.4f}"
    }), use_container_width=True)
else:
    st.info("Select a district to view calculations.")