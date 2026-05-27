import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(layout="wide")

# 1. SETUP
try:
    headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
except Exception:
    st.error("🔒 Security credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "Summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "Mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "Types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
}

# 2. DATA ENGINE
@st.cache_data(ttl=3600)
def fetch_all_data(url):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{url}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

df_summary = fetch_all_data(URLS["Summary"])
df_mapping = fetch_all_data(URLS["Mapping"])
df_types = fetch_all_data(URLS["Types"])

# Standardize IDs
for df in [df_summary, df_mapping, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6).str[:6]

# Merge & Cleanup
df_merged = df_summary.copy()
if not df_mapping.empty:
    df_merged = df_merged.merge(df_mapping[["cds_code", "legislative_district"]], on="cds_code", how="left")
if not df_types.empty:
    df_merged = df_merged.merge(df_types[["cds_code", "district_type"]], on="cds_code", how="left")

# Cleanup
df_merged["assigned_ld"] = df_merged["legislative_district"].apply(lambda x: f"District {int(x)}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged["district_type"].fillna("Unassigned")
df_merged["assigned_county"] = df_merged["cds_code"].str[:2].map(lambda x: {"01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden", "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester", "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex", "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic", "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"}.get(x, "Unassigned"))

# 3. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")

if st.button("🔄 Reset All Filters"):
    st.rerun()

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged["assigned_ld"].unique().tolist(), key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged["assigned_type"].unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged["assigned_county"].unique().tolist()))

df_cascade = df_merged.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]
if sel_county != "All": df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_cascade["district_name"].dropna().unique().tolist()))

# 4. COLUMN ORDERING (The requested matrix columns)
ordered_cols = ["fiscal_year", "adequacy_budget", "uncapped_aid", "actual_state_aid", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]
display_cols = [c for c in ordered_cols if c in df_cascade.columns]

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 District Type Peer Group", "🎯 Academic Return Matrix"])

with tab1:
    if sel_district != "Select...":
        df_render = df_cascade[df_cascade["district_name"] == sel_district].sort_values("fiscal_year")[display_cols]
        st.dataframe(df_render, use_container_width=True)
with tab2:
    st.markdown("#### 📊 District Type Peer Group")
    st.dataframe(df_cascade)