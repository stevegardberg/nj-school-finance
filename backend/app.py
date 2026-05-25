import streamlit as st
import pandas as pd
import requests

# Set page configuration
st.set_page_config(layout="wide")

# 1. HANDSHAKE
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
except:
    st.error("🔒 Security handshake credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/vw_district_cohorts"
}

def fetch(url):
    try:
        r = requests.get(f"{url}?limit=10000", headers=headers, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

# 2. DATA PIPELINE
raw_summary, raw_mapping, raw_types = fetch(URLS["summary"]), fetch(URLS["mapping"]), fetch(URLS["types"])
df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping)
df_all_types = pd.DataFrame(raw_types)

# DYNAMIC COLUMN MAPPING (Ensuring district_name exists regardless of name)
name_cols = [c for c in df_all_types.columns if "name" in c.lower()]
primary_name_col = name_cols[0] if name_cols else "district_name"
df_all_types.rename(columns={primary_name_col: "district_name"}, inplace=True)

# Merge
for df in [df_all_summary, df_all_mapping, df_all_types]:
    if "cds_code" in df.columns: df["cds_code"] = df["cds_code"].astype(str).str.strip().str.zfill(6).str[:6]

df_all_summary = pd.merge(df_all_summary, df_all_types[["cds_code", "district_name"]], on="cds_code", how="left")

# 3. FILTERS & LOGIC
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

f1, f2, f3, f4 = st.columns(4)
with f1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All"] + sorted(list(df_all_summary["assigned_ld"].unique())))
with f4: sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + sorted(df_all_summary["district_name"].dropna().unique().tolist()))

# 4. TABS & FORMATTER
def clean_html_currency_formatter(df):
    return df.to_html(index=False, escape=False)

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_district != "Select a District...":
        df_render = df_all_summary[df_all_summary["district_name"] == sel_district].sort_values("fiscal_year")
        st.write(clean_html_currency_formatter(df_render), unsafe_allow_html=True)
    else:
        st.info("💡 Adjust filters in the top header section to display an individual district's multi-year ledger.")