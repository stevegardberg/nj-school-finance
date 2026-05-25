import streamlit as st
import pandas as pd
import requests

st.set_page_config(layout="wide")

# 1. DATABASE HANDSHAKE
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
    BASE_URL = f"https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
except:
    st.error("Credentials missing.")
    st.stop()

def fetch(endpoint):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}?limit=5000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA PIPELINE
raw_summary = fetch("state_aid_summary")
raw_types = fetch("vw_district_cohorts")

df_summary = pd.DataFrame(raw_summary)
df_types = pd.DataFrame(raw_types)

# CLEAN KEYS
for df in [df_summary, df_types]:
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

# THE CRITICAL MERGE: This brings 'district_name' into the summary table
df_all = pd.merge(df_summary, df_types, on="cds_code", how="left")

# 3. FORMATTER
def clean_html_currency_formatter(df):
    df_f = df.copy()
    for col in df_f.columns:
        if col not in ["Fiscal Year", "District Name"]:
            df_f[col] = df_f[col].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
    return df_f.to_html(index=False, escape=False)

# 4. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
districts = sorted(df_all["district_name"].dropna().unique().tolist())
sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + districts)

# 5. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_dist != "Select a District...":
        df_view = df_all[df_all["district_name"] == sel_dist].sort_values("fiscal_year")
        st.write(clean_html_currency_formatter(df_view[["fiscal_year", "adequacy_budget", "actual_net_payout", "actual_tax_levy"]]), unsafe_allow_html=True)
    else:
        st.info("Select a district to view the matrix.")