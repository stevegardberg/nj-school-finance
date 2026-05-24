import streamlit as st
import pandas as pd
import requests

# Set page configuration to maximum wide-mode for high spreadsheet density
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. LIVE SECURE DATABASE HANDSHAKE WITH ROBUST FAIL-SAFES
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
SUPABASE_URL_DIST_TYPE = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"

NJ_COUNTY_PREFIXES = {
    "01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden",
    "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester",
    "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex",
    "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic",
    "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"
}

def fetch_supabase_table_data(base_url):
    """Paginates and extracts complete datasets safely from active Supabase endpoints."""
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
            else:
                break
        return all_records
    except Exception:
        return []

def clean_html_currency_formatter(df):
    """Transforms raw numeric dataframes into highly polished, clean HTML tables."""
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if col != "Fiscal Year":
            def format_cell(x):
                if pd.isnull(x) or str(x).strip() in ["", "nan", "None"]:
                    return "$0.00"
                val_str = str(x).replace("<b>", "").replace("</b>", "").strip()
                try:
                    val_float = float(val_str)
                    formatted_val = f"${val_float:,.2f}" if val_float >= 0 else f"$-{abs(val_float):,.2f}"
                    if "<b>" in str(x): return f"<b>{formatted_val}</b>"
                    return formatted_val
                except ValueError:
                    return str(x)
            df_formatted[col] = df_formatted[col].apply(format_cell)
    return df_formatted.to_html(index=False, escape=False)

# -----------------------------------------------------------------------------
# 2. RUN DATA PIPELINE FETCHING WITH RESILIENT IN-MEMORY DEFAULTS
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
st.markdown("**NJASBO 2026 Presentation Engine (Cascading Cohort Model Run)**")

raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE)

# Fail-safe check to verify master table returned rows
if not raw_summary:
    st.error("⏳ Pipeline stalled. The master 'state_aid_summary' table is returning empty rows or is locked down by database permissions.")
    st.stop()

# Convert to dataframes
df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_all_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_type", "district_name"])

# Pristine client-side index string cleaning to secure the joins
df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.split('.').str[0].str.zfill(6)

if not df_all_mapping.empty and "cds_code" in df_all_mapping.columns:
    df_all_mapping["cds_code"] = df_all_mapping["cds_code"].astype(str).str.split('.').str[0].str.zfill(6)
    leg_dict = dict(zip(df_all_mapping["cds_code"], df_all_mapping["legislative_district"]))
else:
    leg_dict = {}

if not df_all_types.empty and "cds_code" in df_all_types.columns:
    df_all_types["cds_code"] = df_all_types["cds_code"].astype(str).str.split('.').str[0].str.zfill(6)
    type_dict = dict(zip(df_all_types["cds_code"], df_all_types["district_type"]))
else:
    type_dict = {}

# Fast-cast financial variables safely
numeric_targets = ["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]
for target in numeric_targets:
    if target in df_all_summary.columns:
        df_all_summary[target] = pd.to_numeric(df_all_summary[target]).fillna(0.0)
    else:
        df_all_summary[target] = 0.0

# Establish mapping structural references across all ledger rows
df_all_summary["lfs_delta"] = df_all_summary["actual_tax_levy"] - df_all_summary["local_fair_share"]
df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "District 25")

# FIX: Implement a strict fallback grouping string if a specific code is missing from the mapping sheet
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "E. K-12 / 0 - 1800"))
df_all_summary["assigned_county"] = df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned"))

# -----------------------------------------------------------------------------
# 3. INITIALIZE STATE HOOKS FOR RESETTING CONTROLS
# -----------------------------------------------------------------------------
if "reset_trigger" not in st.session_state:
    st.session_state.reset_trigger = False

def reset_filter_chain():
    st.session_state.reset_trigger = True

master_ld_options = sorted(list(set(df_all_summary["assigned_ld"].dropna())))
master_type_options = sorted(list(set(df_all_summary["assigned_type"].dropna())))

# -----------------------------------------------------------------------------
# 4. REFINED HIERARCHICAL CASCADING HEADER FILTERS
# -----------------------------------------------------------------------------
with st.container():
    st.markdown("---")
    r_col1, r_col2 = st.columns([6, 1])
    with r_col2:
        st.button("🔄 Reset All Filters", on_click=reset_filter_chain, use_container_width=True)

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    
    # Tier 1: Primary Macro Selectors (Initializes cleanly to "All")
    with f_col1:
        sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options, index=0)
    with f_col2:
        sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options, index=0)

    # Process first stage slice
    df_cascade = df_all_summary.copy()
    if sel_ld != "All Legislative Districts":
        df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
    if sel_type != "All District Types":
        df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

    # Tier 2: Secondary Downstream Selectors (Narrows dynamically based on Tier 1 choices)
    with f_col3:
        available_counties = sorted(list(set(df_cascade["assigned_county"].dropna())))
        sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + available_counties, index=0)

    if sel_county != "All Counties":
        df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

    with f_col4:
        available_towns = sorted(list(set(df_cascade["district_name"].dropna())))
        sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + available_towns, index=0)

    # Force immediate layout draw if reset button clicked
    if st.session_state.reset_trigger:
        st.session_state.reset_trigger = False
        st.rerun()
        
    st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

# -----------------------------------------------------------------------------
# 5. NEW STRUCTURAL MATRIX COLUMN SEQUENCE DEFINITIONS
# -----------------------------------------------------------------------------
rename_map = {
    "fiscal_year": "Fiscal Year", 
    "adequacy_budget": "[1] Adequacy Budget Base",
    "uncapped_aid": "[2] Uncapped SFRA Formula Target", 
    "actual_net_payout": "[3] Actual State Aid", 
    "s2_adjustment": "[4] Legislative S2 Adjustment Delta",
    "local_fair_share": "[5] Local Fair Share (LFS)",
    "actual_tax_levy": "[6] Actual Local Tax Levy",
    "lfs_delta": "[7] Amt Over/(Under) LFS",
    "equalized_valuation": "[8] Equalized Property Valuation", 
    "district_income": "[9] Aggregate District Income"
}
ordered_cols = ["fiscal_year", "adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "lfs_delta", "equalized_valuation", "district_income"]

# -----------------------------------------------------------------------------
# 6. RENDER DATA ARCHITECTURES
# -----------------------------------------------------------------------------
with tab1:
    # --- TIER 1: Individual Target District Matrix ---
    if sel_district and sel_district != "Select a District...":
        st.markdown(f"#### 📍 Target District Multi-Year Ledger — {sel_district}")
        df_district_history = df_all_summary[df_all_summary["district_name"] == sel_district].sort_values("fiscal_year").copy()
        
        if not df_district_history.empty:
            df_render = df_district_history[[c for c in ordered_cols if c in df_district_history.columns]].copy()
            
            tot_s2 = df_render["s2_adjustment"].sum()
            tot_lfs = df_render["lfs_delta"].sum()
            sum_row = {col: "" for col in df_render.columns}
            sum_row["fiscal_year"] = "<b>TOTAL SUMMARY</b>"
            sum_row["s2_adjustment"] = f"<b>{tot_s2}</b>"
            sum_row["lfs_delta"] = f"<b>{tot_lfs}</b>"
            
            df_master_final = pd.concat([df_render, pd.DataFrame([sum_row])], ignore_index=True)
            df_master_final.rename(columns=rename_map, inplace=True)
            st.write(clean_html_currency_formatter(df_master_final), unsafe_allow_html=True)
            
            current_active_ld = df