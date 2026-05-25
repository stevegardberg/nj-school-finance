import streamlit as st
import pandas as pd
import requests

# Set page configuration to maximum wide-mode for high spreadsheet density
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. LIVE SECURE DATABASE HANDSHAKE WITH SYSTEM RESILIENCY
# -----------------------------------------------------------------------------
try:
    headers = {
        "apikey": st.secrets["headers"]["apikey"],
        "Authorization": st.secrets["headers"]["Authorization"]
    }
except Exception:
    st.error("🔒 Security handshake credentials missing. Please configure Streamlit Cloud Advanced Secrets.")
    st.stop()

SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
SUPABASE_URL_SUMMARY = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary"
SUPABASE_URL_MAPPING = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping"
# Using your confirmed table name
SUPABASE_URL_DIST_TYPE = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/vw_district_cohorts"

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
                    if "<b>" in str(x): return f"<b>{formatted_val}</b>"
                    return formatted_val
                except ValueError: return str(x)
            df_formatted[col] = df_formatted[col].apply(format_cell)
    return df_formatted.to_html(index=False, escape=False)

# -----------------------------------------------------------------------------
# 2. RUN DATA PIPELINE FETCHING
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE)

if not raw_summary:
    st.error("⏳ Pipeline stalled. The master 'state_aid_summary' table is returning empty rows.")
    st.stop()

df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_all_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_type", "district_name"])

# Normalize CDS codes
for df in [df_all_summary, df_all_mapping, df_all_types]:
    if "cds_code" in df.columns:
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# --- DATA REPAIR LAYER: Force metadata into summary ---
df_all_summary = pd.merge(df_all_summary, df_all_types, on="cds_code", how="left")
df_all_summary["district_name"] = df_all_summary["district_name"].fillna("Unknown District")
# --- END REPAIR ---

# Fast-cast financial numbers
numeric_targets = ["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]
for target in numeric_targets:
    if target in df_all_summary.columns:
        df_all_summary[target] = pd.to_numeric(df_all_summary[target], errors='coerce').fillna(0.0)

# Mappings
leg_dict = dict(zip(df_all_mapping["cds_code"], df_all_mapping["legislative_district"])) if not df_all_mapping.empty else {}
type_dict = dict(zip(df_all_types["cds_code"], df_all_types["district_type"])) if not df_all_types.empty else {}

df_all_summary["lfs_delta"] = df_all_summary.get("actual_tax_levy", 0) - df_all_summary.get("local_fair_share", 0)
df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned LD")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "Unassigned Type"))
df_all_summary["assigned_county"] = df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned"))

# 3. FILTERS
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + sorted(list(set(df_all_summary["assigned_ld"].dropna()))))
with f_col2: sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + sorted(list(set(df_all_summary["assigned_type"].dropna()))))

df_cascade = df_all_summary.copy()
if sel_ld != "All Legislative Districts": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
if sel_type != "All District Types": df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

with f_col3: sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + sorted(list(set(df_cascade["assigned_county"].dropna()))))
if sel_county != "All Counties": df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

with f_col4: sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + sorted(list(df_cascade["district_name"].dropna().unique())))

st.markdown("---")

# 4. TABS
tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

rename_map = {"fiscal_year": "Fiscal Year", "adequacy_budget": "[1] Adequacy", "actual_net_payout": "[3] State Aid", "local_fair_share": "[5] LFS", "actual_tax_levy": "[6] Tax Levy"}
ordered_cols = ["fiscal_year", "adequacy_budget", "actual_net_payout", "local_fair_share", "actual_tax_levy"]

with tab1:
    if sel_district != "Select a District...":
        df_render = df_all_summary[df_all_summary["district_name"] == sel_district][ordered_cols].sort_values("fiscal_year")
        st.write(clean_html_currency_formatter(df_render.rename(columns=rename_map)), unsafe_allow_html=True)
    else:
        st.info("Select a district.")