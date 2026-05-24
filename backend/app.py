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

if not raw_summary:
    st.error("⏳ Pipeline stalled. The master 'state_aid_summary' table is returning empty rows.")
    st.stop()

# Convert to dataframes with clean safety backstops
df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_all_types = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_type", "district_name"])

# Pristine client-side string padding
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

# Fast-cast financial numbers safely
numeric_targets = ["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]
for target in numeric_targets:
    if target in df_all_summary.columns:
        df_all_summary[target] = pd.to_numeric(df_all_summary[target]).fillna(0.0)
    else:
        df_all_summary[target] = 0.0

df_all_summary["lfs_delta"] = df_all_summary["actual_tax_levy"] - df_all_summary["local_fair_share"]
df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned LD")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "Unassigned Type"))
df_all_summary["assigned_county"] = df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned"))

# Generate static, unfiltered lists to keep selections resilient
master_ld_options = sorted(list(set(df_all_summary[df_all_summary["assigned_ld"] != "Unassigned LD"]["assigned_ld"].dropna())))
master_type_options = sorted(list(set(df_all_summary[df_all_summary["assigned_type"] != "Unassigned Type"]["assigned_type"].dropna())))

# -----------------------------------------------------------------------------
# 3. REFINED DECOUPLED CASCADING HEADER FILTERS
# -----------------------------------------------------------------------------
with st.container():
    st.markdown("---")
    
    # Reset layout capability button
    r_col1, r_col2 = st.columns([6, 1])
    with r_col2:
        if st.button("🔄 Reset All Filters", use_container_width=True):
            st.rerun()

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    
    with f_col1:
        sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options, index=0)
    with f_col2:
        sel_type = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options, index=0)

    # Process macro cascade slice
    df_cascade = df_all_summary.copy()
    if sel_ld != "All Legislative Districts":
        df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
    if sel_type != "All District Types":
        df_cascade = df_cascade[df_cascade["assigned_type"] == sel_type]

    with f_col3:
        available_counties = sorted(list(set(df_cascade["assigned_county"].dropna())))
        if "Unassigned" in available_counties: available_counties.remove("Unassigned")
        sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + available_counties, index=0)

    if sel_county != "All Counties":
        df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

    with f_col4:
        # Pull alphabetical list of unique matching towns
        available_towns = sorted(list(set(df_cascade["district_name"].dropna())))
        sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + available_towns, index=0)

    st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

# -----------------------------------------------------------------------------
# 4. STRUCTURAL COLUMN DEFINITIONS
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
# 5. RENDER THE LAYERED INTERFACE PANELS
# -----------------------------------------------------------------------------
with tab1:
    current_active_ld, current_active_type = None, None

    # --- TIER 1: TARGET DISTRICT MATRIX ---
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
            
            # Lock variables from individual row profile selection to drive fallback peer averages
            current_active_ld = df_district_history["assigned_ld"].iloc[0]
            current_active_type = df_district_history["assigned_type"].iloc[0]
    else:
        st.info("💡 Adjust cascading filter parameters in the top header section to display an individual district's multi-year ledger.")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- TIER 2: COHORT PEER GROUP AVERAGE MATRICES ---
    st.markdown("#### 👥 Peer Group Benchmark Aggregator & Comparative Performance Matrix")
    
    # Establish distinct fallback logic bounds
    target_peer_ld = sel_ld if sel_ld != "All Legislative Districts" else (current_active_ld if current_active_ld else "All Legislative Districts")
    target_peer_type = sel_type if sel_type != "All District Types" else (current_active_type if current_active_type else "All District Types")
    
    st.caption(f"Displays mathematically computed multi-year group averages matching: **{target_peer_ld}** | **{target_peer_type}**")
    
    df_peer_pool = df_all_summary.copy()
    if target_peer_ld != "All Legislative Districts":
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_ld"] == target_peer_ld]
    if target_peer_type != "All District Types":
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_type"] == target_peer_type]
        
    if not df_peer_pool.empty and (target_peer_ld != "All Legislative Districts" or target_peer_type != "All District Types"):
        df_grouped_averages = df_peer_pool.groupby("fiscal_year")[ordered_cols[1:]].mean().reset_index()
        df_peer_render = df_grouped_averages.sort_values("fiscal_year").copy()
        df_peer_render.rename(columns=rename_map, inplace=True)
        st.write(clean_html_currency_formatter(df_peer_render), unsafe_allow_html=True)
    else:
        st.caption("Select a local target district or specify a primary cohort criteria to activate peer group mathematical models.")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- TIER 3: STATE-WIDE MACRO BASELINE ---
    st.markdown("#### 🌐 State-Wide Structural Averages Baseline")
    st.caption("Displays the macro baseline average across all combined public school systems in New Jersey per year.")
    
    df_state_averages = df_all_summary.groupby("fiscal_year")[ordered_cols[1:]].mean().reset_index()
    df_state_render = df_state_averages.sort_values("fiscal_year").copy()
    df_state_render.rename(columns=rename_map, inplace=True)
    st.write(clean_html_currency_formatter(df_state_render), unsafe_allow_html=True)

with tab2:
    st.markdown("#### UFB Appropriations Component Ledger")
with tab3:
    st.markdown("#### Return on Academic Investment Insights (ROAI)")