import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(layout="wide")

# 1. AUTH & CONFIG
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

# 2. DATA ENGINE (PAGINATED)
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

# Load data
df_summary = fetch_all_data(URLS["Summary"])
df_mapping = fetch_all_data(URLS["Mapping"])
df_types = fetch_all_data(URLS["Types"])

# 3. JOIN & CLEANUP ENGINE
# Standardize keys
for df in [df_summary, df_mapping, df_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.zfill(6).str[:6]

# Merge logic (Safely handle missing tables)
df_merged = df_summary.copy()
if not df_mapping.empty and "legislative_district" in df_mapping.columns:
    df_merged = df_merged.merge(df_mapping[["cds_code", "legislative_district"]], on="cds_code", how="left")
if not df_types.empty and "district_type" in df_types.columns:
    df_merged = df_merged.merge(df_types[["cds_code", "district_type"]], on="cds_code", how="left")

# Assign metadata
df_merged["assigned_ld"] = df_merged["legislative_district"].apply(lambda x: f"District {x}" if pd.notnull(x) else "Unassigned")
df_merged["assigned_type"] = df_merged["district_type"].fillna("Unassigned")
df_merged["assigned_county"] = df_merged["cds_code"].str[:2].map(lambda x: {"01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden", "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester", "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex", "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic", "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"}.get(x, "Unassigned"))

# Sorting
def extract_num(s):
    nums = re.findall(r'\d+', str(s))
    return int(nums[0]) if nums else 0

master_ld = sorted([ld for ld in df_merged["assigned_ld"].unique() if ld != "Unassigned"], key=extract_num)
master_type = sorted([t for t in df_merged["assigned_type"].unique() if t != "Unassigned"])

# 4. UI FILTERS
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + master_ld)
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + master_type)
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged["assigned_county"].unique().tolist()))

# Cascade logic
df_cascade = df_merged.copy()
if sel_ld != "All": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]
if sel_county != "All": df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_cascade["district_name"].unique().tolist()))

# 5. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 District Type Peer Group", "🎯 Academic Return Matrix"])
with tab1:
    st.write(f"Total Records Loaded: {len(df_merged)}")
    if sel_district != "Select...":
        st.dataframe(df_cascade[df_cascade["district_name"] == sel_district].sort_values("fiscal_year"))
with tab2:
    st.markdown("#### 📊 District Type Peer Group")
    if sel_type != "All":
        st.dataframe(df_cascade[df_cascade["assigned_type"] == sel_type])