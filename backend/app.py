import streamlit as st
import pandas as pd
import requests

# Set page configuration
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. LIVE SECURE DATABASE HANDSHAKE
# -----------------------------------------------------------------------------
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

def fetch_supabase_table_data(base_url):
    all_records = []
    page = 0
    while True:
        response = requests.get(f"{base_url}?limit=1000&offset={page*1000}", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if not data: break
            all_records.extend(data)
            page += 1
        else: break
    return all_records

def clean_html_currency_formatter(df):
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if col != "Fiscal Year":
            df_formatted[col] = df_formatted[col].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
    return df_formatted.to_html(index=False, escape=False)

# -----------------------------------------------------------------------------
# 2. DATA PIPELINE
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
raw_summary = fetch_supabase_table_data(URLS["Summary"])
raw_mapping = fetch_supabase_table_data(URLS["Mapping"])
raw_types = fetch_supabase_table_data(URLS["Types"])

df_all_summary = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame()
df_all_mapping = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame()
df_all_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame()

df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.zfill(6).str[:6]

# Dictionary Mapping
leg_dict = dict(zip(df_all_mapping["cds_code"].str.zfill(6), df_all_mapping["legislative_district"])) if not df_all_mapping.empty else {}
type_dict = dict(zip(df_all_types["cds_code"].str.zfill(6), df_all_types["district_type"])) if not df_all_types.empty else {}

df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "Unassigned"))
df_all_summary["assigned_county"] = df_all_summary["cds_code"].str[:2].map(lambda x: NJ_COUNTY_PREFIXES.get(x, "Unassigned"))

master_ld_options = sorted([ld for ld in df_all_summary["assigned_ld"].unique() if ld != "Unassigned"], key=lambda x: int(x.split()[-1]) if x != "Unassigned" else 0)
master_type_options = sorted([t for t in df_all_summary["assigned_type"].unique() if t != "Unassigned"])

# -----------------------------------------------------------------------------
# 3. FILTERS & TABS
# -----------------------------------------------------------------------------
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    with c1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options)
    with c2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options)
    
    df_cascade = df_all_summary.copy()
    if sel_ld != "All Legislative Districts": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
    if sel_type != "All District Types": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]
    
    with c3: sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + sorted(df_cascade["assigned_county"].dropna().unique().tolist()))
    with c4: sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + sorted(df_cascade["district_name"].dropna().unique().tolist()))

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

with tab1:
    if sel_district != "Select a District...":
        st.markdown(f"#### 📍 Target District Ledger — {sel_district}")
        df_render = df_all_summary[df_all_summary["district_name"] == sel_district]
        st.write(clean_html_currency_formatter(df_render), unsafe_allow_html=True)
    else:
        st.info("Select a district to view matrix.")