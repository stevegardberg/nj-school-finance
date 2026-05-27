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

NJ_COUNTY_PREFIXES = {"01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden", "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester", "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex", "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic", "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"}

def fetch_and_validate(url, required_cols):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if not data: return pd.DataFrame(columns=required_cols)
        df = pd.DataFrame(data)
        return df # Keep all columns for now to prevent drop errors
    return pd.DataFrame(columns=required_cols)

# Load data
df_summary = fetch_and_validate(URLS["Summary"], ["cds_code", "district_name"])
df_mapping = fetch_and_validate(URLS["Mapping"], ["cds_code", "legislative_district"])
df_types = fetch_and_validate(URLS["Types"], ["cds_code", "district_type"])

# Debugging Sidebar
st.sidebar.markdown("### 🔍 Data Diagnostics")
st.sidebar.write(f"Summary Rows: {len(df_summary)}")
st.sidebar.write(f"Type Table Rows: {len(df_types)}")
st.sidebar.write("Columns in Type Table:", list(df_types.columns))

# Logic
df_summary["cds_code"] = df_summary["cds_code"].astype(str).str.zfill(6).str[:6]
df_merged = df_summary.copy()

if not df_mapping.empty:
    df_mapping["cds_code"] = df_mapping["cds_code"].astype(str).str.zfill(6).str[:6]
    df_merged = df_merged.merge(df_mapping, on="cds_code", how="left")

if not df_types.empty:
    df_types["cds_code"] = df_types["cds_code"].astype(str).str.zfill(6).str[:6]
    df_merged = df_merged.merge(df_types, on="cds_code", how="left")

# Metadata
df_merged["assigned_ld"] = df_merged.get("legislative_district", pd.Series([None]*len(df_merged))).apply(lambda x: f"District {x}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged.get("district_type", pd.Series(["Unassigned"]*len(df_merged)))
df_merged["assigned_county"] = df_merged["cds_code"].str[:2].map(lambda x: NJ_COUNTY_PREFIXES.get(x, "Unassigned"))

# Filters
master_ld = sorted([ld for ld in df_merged["assigned_ld"].unique() if ld != "Unassigned"], key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)
master_type = sorted([t for t in df_merged["assigned_type"].unique() if t != "Unassigned"])

# UI
c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + master_ld)
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + master_type)
df_cascade = df_merged.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_cascade["assigned_county"].unique().tolist()))
if sel_county != "All": df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]
sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_cascade["district_name"].unique().tolist()))

tab1, tab2, tab3 = st.tabs(["⚖️ MATRIX", "📊 PEER GROUP", "🎯 RETURN"])
with tab1: st.write("Matrix ready.")