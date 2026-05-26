import streamlit as st
import pandas as pd
import requests

# Set page configuration
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. LIVE SECURE DATABASE HANDSHAKE
# -----------------------------------------------------------------------------
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
except Exception:
    st.error("🔒 Security handshake credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "Summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "Mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "Types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
}

NJ_COUNTY_PREFIXES = {
    "01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden",
    "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester",
    "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex",
    "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic",
    "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"
}

def fetch_supabase_table_data(base_url):
    all_records = []
    page = 0
    page_size = 1000
    while True:
        offset = page * page_size
        response = requests.get(f"{base_url}?limit={page_size}&offset={offset}", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if not data: break
            all_records.extend(data)
            page += 1
        else: break
    return all_records

# -----------------------------------------------------------------------------
# 2. DATA PIPELINE
# -----------------------------------------------------------------------------
raw_summary = fetch_supabase_table_data(URLS["Summary"])
raw_mapping = fetch_supabase_table_data(URLS["Mapping"])
raw_types = fetch_supabase_table_data(URLS["Types"])

df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping)
df_all_types = pd.DataFrame(raw_types)

# Normalization
df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.zfill(6).str[:6]

# Strict Mapping with Column Existence Check
leg_dict = dict(zip(df_all_mapping["cds_code"].astype(str).str.zfill(6), df_all_mapping["legislative_district"])) if not df_all_mapping.empty and "cds_code" in df_all_mapping.columns else {}
type_dict = dict(zip(df_all_types["cds_code"].astype(str).str.zfill(6), df_all_types["district_type"])) if not df_all_types.empty and "cds_code" in df_all_types.columns else {}

df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(leg_dict)
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(type_dict)
df_all_summary["assigned_county"] = df_all_summary["cds_code"].str[:2].map(NJ_COUNTY_PREFIXES)

# Filter Options
master_ld_options = sorted([f"District {int(ld)}" for ld in df_all_summary["assigned_ld"].dropna().unique()])
master_type_options = sorted(df_all_summary["assigned_type"].dropna().unique().tolist())

# -----------------------------------------------------------------------------
# 3. UI FILTERS
# -----------------------------------------------------------------------------
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    with c1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options)
    with c2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options)
    
    df_cascade = df_all_summary.copy()
    if sel_ld != "All Legislative Districts": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld.replace("District ", "")]
    if sel_type != "All District Types": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]
    
    with c3: sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + sorted(df_cascade["assigned_county"].dropna().unique().tolist()))
    with c4: sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + sorted(df_cascade["district_name"].dropna().unique().tolist()))

# -----------------------------------------------------------------------------
# 4. RENDER
# -----------------------------------------------------------------------------
if sel_district != "Select a District...":
    df_render = df_all_summary[df_all_summary["district_name"] == sel_district]
    st.table(df_render)