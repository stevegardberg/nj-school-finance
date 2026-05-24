import streamlit as st
import pandas as pd
import requests

# Force screen-width data density configuration
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. DATABASE GATEWAY CONNECTORS
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
    """Paginates and extracts complete records safely from target Supabase endpoints."""
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
    """Transforms raw numeric arrays into polished, web-ready HTML spreadsheet tables."""
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
# 2. DATA PIPELINE FETCHING & PRE-COMPUTATIONS
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
st.markdown("**NJASBO 2026 Presentation Engine (Cascading Filter Topology)**")

raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE)

if not raw_summary:
    st.error("⏳ Data sync stalled. Check active cloud network pipeline configurations.")
    st.stop()

df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping)
df_all_types = pd.DataFrame(raw_types)

# Standardize relational index formats
df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.split('.').str[0].str.zfill(6)

leg_dict = dict(zip(df_all_mapping["cds_code"].astype(str).str.split('.').str[0].str.zfill(6), df_all_mapping["legislative_district"])) if not df_all_mapping.empty else {}
type_dict = dict(zip(df_all_types["cds_code"].astype(str).str.split('.').str[0].str.zfill(6), df_all_types["district_type"])) if not df_all_types.empty else {}

# Fast-cast numeric formats
numeric_targets = ["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]
for target in numeric_targets:
    df_all_summary[target] = pd.to_numeric(df_all_summary.get(target, 0.0)).fillna(0.0)

df_all_summary["lfs_delta"] = df_all_summary["actual_tax_levy"] - df_all_summary["local_fair_share"]
df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "District 25")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "E. K-12 / 0 - 1800"))
df_all_summary["assigned_county"] = df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned"))

# -----------------------------------------------------------------------------
# 3. INITIALIZE STATE HOOKS FOR RESETTING MATRIX CONTROLS
# -----------------------------------------------------------------------------
if "reset_trigger" not in st.session_state:
    st.session_state.reset_trigger = False

# Function to clear selection values instantly back to state baseline configurations
def reset_filter_chain():
    st.session_state.reset_trigger = True

# Extract initial state-wide master boundary options
master_ld_options = sorted(list(set(df_all_summary["assigned_ld"].dropna())))
master_type_options = sorted(list(set(df_all_summary["assigned_type"].dropna())))

# -----------------------------------------------------------------------------
# 4. PRIMARY CASCADING FILTER LOGIC HEADER VIEW (REQUIREMENT 1)
# -----------------------------------------------------------------------------
with st.container():
    st.markdown("---")
    
    # Reset button configuration track anchor
    r_col1, r_col2 = st.columns([6, 1])
    with r_col2:
        st.button("🔄 Reset All Filters", on_click=reset_filter_chain, use_container_width=True)

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    
    # Layer A: Primary Dropdowns (Legislative and Operational Type Cohorts)
    with f_col1:
        if st.session_state.reset_trigger:
            ld_index = 0
        else:
            ld_index = 0
        sel_ld = st.selectbox("1️⃣ Primary Legislative Filter:", ["All Districts"] + master_ld_options, index=ld_index)
        
    with f_col2:
        sel_type = st.selectbox("2️⃣ Primary Type Filter:", ["All Types"] + master_type_options, index=0)

    # Secondary Cascade Data Computation Pool
    df_cascade_pool = df_all_summary.copy()
    if sel_ld != "All Districts":
        df_cascade_pool = df_cascade_pool[df_cascade_pool["assigned_ld"] == sel_ld]
    if sel_type != "All Types":
        df_cascade_pool = df_cascade_pool[df_cascade_pool["assigned_type"] == sel_type]

    # Layer B: Downstream Dropdowns (County & District lists contract relationally)
    with f_col3:
        available_counties = sorted(list(set(df_cascade_pool["assigned_county"].dropna())))
        
        # Safe fallback defaults if reset trigger is clicked
        if "Morris" in available_counties and not st.session_state.reset_trigger:
            default_co_idx = available_counties.index("Morris")
        else:
            default_co_idx = 0
            
        sel_county = st.selectbox("3️⃣ Cascaded County:", available_counties, index=default_co_idx)

    # Apply County filter to the final town list selection
    df_cascade_pool = df_cascade_pool[df_cascade_pool["assigned_county"] == sel_county]

    with f_col4:
        available_towns = sorted(list(set(df_cascade_pool["district_name"].dropna())))
        
        if "Boonton Town" in available_towns and not st.session_state.reset_trigger:
            default_tn_idx = available_towns.index("Boonton Town")
        else:
            default_tn_idx = 0
            
        sel_district = st.selectbox("4️⃣ Target Local District:", available_towns, index=default_tn_idx)

    # Disengage structural reset state trigger flag once loop completes successfully
    st.session_state.reset_trigger = False
    st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

# -----------------------------------------------------------------------------
# 5. NEW STRUCTURAL ALIGNMENT INDEX DICTIONARY MAPS (REQUIREMENT 2)
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
# 6. RENDER DATA ARCHITECTURES IN WEB INTERFACE PANELS
# -----------------------------------------------------------------------------
with tab1:
    # --- LAYER 1: Target Individual Operational Matrices ---
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
    else:
        st.warning("⏳ Selection parameter fields calculating pipeline adjustments...")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- LAYER 2: Regional Peer Metrics Average Layer ---
    st.markdown("#### 👥 Peer Group Benchmark Aggregator & Comparative Performance Matrix")
    st.caption(f"Displays mathematically computed multi-year group averages matching: **{sel_ld}** | **{sel_type}**")
    
    df_peer_pool = df_all_summary.copy()
    if sel_ld != "All Districts":
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_ld"] == sel_ld]
    if sel_type != "All Types":
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_type"] == sel_type]
        
    if not df_peer_pool.empty:
        df_grouped_averages = df_peer_pool.groupby("fiscal_year")[ordered_cols[1:]].mean().reset_index()
        df_peer_render = df_grouped_averages.sort_values("fiscal_year").copy()
        df_peer_render.rename(columns=rename_map, inplace=True)
        st.write(clean_html_currency_formatter(df_peer_render), unsafe_allow_html=True)

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- LAYER 3: Absolute Macro State Baseline ---
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