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
df_summary = pd.DataFrame(fetch("state_aid_summary"))
df_types = pd.DataFrame(fetch("vw_district_cohorts"))

# Clean keys
for df in [df_summary, df_types]:
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6)

# MERGE
df_all = pd.merge(df_summary, df_types, on="cds_code", how="left")

# DYNAMIC COLUMN FINDER: Finds the column that actually holds the name
name_cols = [c for c in df_all.columns if "district_name" in c.lower() or "name" in c.lower()]
primary_name_col = name_cols[0] if name_cols else None

if not primary_name_col:
    st.error(f"Critical Error: Could not find a district name column. Available columns: {df_all.columns.tolist()}")
    st.stop()

# 3. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
districts = sorted(df_all[primary_name_col].dropna().unique().tolist())
sel_dist = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + districts)

# 4. FORMATTER
def clean_html_currency_formatter(df):
    df_f = df.copy()
    # Apply to all numeric-looking columns
    for col in df_f.columns:
        if df_f[col].dtype in ['float64', 'int64']:
            df_f[col] = df_f[col].apply(lambda x: f"${x:,.2f}")
    return df_f.to_html(index=False, escape=False)

# 5. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_dist != "Select a District...":
        df_view = df_all[df_all[primary_name_col] == sel_dist].sort_values("fiscal_year")
        st.write(clean_html_currency_formatter(df_view), unsafe_allow_html=True)
    else:
        st.info("Select a district to view the matrix.")