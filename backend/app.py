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
    st.error("🔒 Security credentials missing.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
SUPABASE_URL_SUMMARY = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary"
SUPABASE_URL_MAPPING = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping"
SUPABASE_URL_DIST_TYPE = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"

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
    try:
        while True:
            offset = page * page_size
            url = f"{base_url}?limit={page_size}&offset={offset}"
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                page_data = response.json()
                if not page_data: break
                all_records.extend(page_data)
                if len(page_data) < page_size: break
                page += 1
            else: break
        return all_records
    except Exception: return []

def clean_html_currency_formatter(df):
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if col != "Fiscal Year":
            def format_cell(x):
                if pd.isnull(x) or str(x).strip() in ["", "nan", "None"]: return "$0.00"
                val_str = str(x).replace("<b>", "").replace("</b>", "").strip()
                try:
                    val_float = float(val_str)
                    formatted_val = f"${val_float:,.2f}" if val_float >= 0 else f"$-{abs(val_float):,.2f}"
                    return f"<b>{formatted_val}</b>" if "<b>" in str(x) else formatted_val
                except ValueError: return str(x)
            df_formatted[col] = df_formatted[col].apply(format_cell)
    return df_formatted.to_html(index=False, escape=False)

# -----------------------------------------------------------------------------
# 2. DATA PIPELINE
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE)

df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_all_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_type", "district_name"])

df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Build Dictionaries
leg_dict = dict(zip(df_all_mapping["cds_code"].astype(str).str.zfill(6), df_all_mapping["legislative_district"].astype(str))) if not df_all_mapping.empty else {}
type_dict = dict(zip(df_all_types["cds_code"].astype(str).str.zfill(6), df_all_types["district_type"].astype(str))) if not df_all_types.empty else {}

# Enrich Dataframe
df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned LD")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "Unassigned Type"))
df_all_summary["assigned_county"] = df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned"))

# Numeric Sort for LD Filter
valid_ld = [ld for ld in df_all_summary["assigned_ld"].unique() if ld != "Unassigned LD"]
master_ld_options = sorted(valid_ld, key=lambda x: int(x.replace("District ", "")) if "District " in x else 0)
master_type_options = sorted([t for t in df_all_summary["assigned_type"].unique() if t != "Unassigned Type"])

# -----------------------------------------------------------------------------
# 3. FILTERS & RENDER
# -----------------------------------------------------------------------------
with st.container():
    if st.button("🔄 Reset All Filters"): st.rerun()
    f1, f2, f3, f4 = st.columns(4)
    with f1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options)
    with f2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options)
    
    df_cascade = df_all_summary.copy()
    if sel_ld != "All Legislative Districts": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
    if sel_type != "All District Types": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]
    
    with f3: sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + sorted([c for c in df_cascade["assigned_county"].unique() if c != "Unassigned"]))
    if sel_county != "All Counties": df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]
    
    with f4: sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + sorted(df_cascade["district_name"].dropna().unique()))

tab1, tab2, tab3 = st.tabs(["⚖️ VALIDATION MATRIX", "📊 Budget Explorer", "🎯 Academic Return"])
with tab1:
    if sel_district != "Select a District...":
        df_render = df_all_summary[df_all_summary["district_name"] == sel_district]
        st.write(clean_html_currency_formatter(df_render), unsafe_allow_html=True)