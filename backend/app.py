import streamlit as st
import pandas as pd
import requests

# Set page configuration to maximum wide-mode for high data density
st.set_page_config(layout="wide")

# -----------------------------------------------------------------------------
# 1. LIVE RE-AUTHENTICATED HANDSHAKE
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
    """Transforms raw numeric dataframes into polished, clean HTML tables."""
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
# 2. RUN META-DATA PIPELINE & RE-LINK THE NEW CSV LOOKUPS
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
st.markdown("**NJASBO 2026 Presentation Engine (Relational CSV Taxonomy Run)**")

raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE)

if not raw_summary:
    st.error("⏳ Pipeline stalled. Unable to communicate with the master state aid ledger storage.")
    st.stop()

df_all_summary = pd.DataFrame(raw_summary)
df_all_mapping = pd.DataFrame(raw_mapping)
df_all_types = pd.DataFrame(raw_types)

# Standardize text indexes
df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.split('.').str[0].str.zfill(6)

# Create dictionaries for fast in-memory lookups
leg_dict = dict(zip(df_all_mapping["cds_code"].astype(str).str.split('.').str[0].str.zfill(6), df_all_mapping["legislative_district"])) if not df_all_mapping.empty else {}
type_dict = dict(zip(df_all_types["cds_code"].astype(str).str.split('.').str[0].str.zfill(6), df_all_types["district_type"])) if not df_all_types.empty else {}

numeric_targets = ["uncapped_aid", "s2_adjustment", "actual_net_payout", "adequacy_budget", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]
for target in numeric_targets:
    df_all_summary[target] = pd.to_numeric(df_all_summary.get(target, 0.0)).fillna(0.0)

# Apply unified structural columns
df_all_summary["lfs_delta"] = df_all_summary["actual_tax_levy"] - df_all_summary["local_fair_share"]
df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "District 25")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "E. K-12 / 0 - 1800"))

# Filter layout dropdown options setup
county_list = sorted(list(set(df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned")).dropna())))
if "Morris" not in county_list: county_list.insert(0, "Morris")

# -----------------------------------------------------------------------------
# 3. HEADER MENUS (REQUIREMENT 1)
# -----------------------------------------------------------------------------
with st.container():
    st.markdown("---")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    
    with f_col1:
        sel_county = st.selectbox("Select County:", county_list, index=county_list.index("Morris") if "Morris" in county_list else 0)
    with f_col2:
        df_filtered_county = df_all_summary[df_all_summary["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "")) == sel_county]
        available_towns = sorted(list(set(df_filtered_county["district_name"].dropna())))
        if not available_towns: available_towns = ["Boonton Town"]
        sel_district = st.selectbox("Select School District:", available_towns, index=available_towns.index("Boonton Town") if "Boonton Town" in available_towns else 0)
    with f_col3:
        ld_options = sorted(list(set(df_all_summary["assigned_ld"].dropna())))
        ld_options.insert(0, "All Districts")
        sel_ld_filter = st.selectbox("Filter Peer Legislative District:", ld_options)
    with f_col4:
        type_options = sorted(list(set(df_all_summary["assigned_type"].dropna())))
        type_options.insert(0, "All Types")
        sel_type_filter = st.selectbox("Filter Peer District Type Structure:", type_options)
    st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

rename_map = {
    "fiscal_year": "Fiscal Year", 
    "uncapped_aid": "[1] Uncapped SFRA Formula Target", 
    "s2_adjustment": "[2] Legislative S2 Adjustment Delta",
    "actual_net_payout": "[3] Actual State Aid", 
    "adequacy_budget": "[4] Adequacy Budget Base",
    "local_fair_share": "[5] Local Fair Share (LFS)",
    "actual_tax_levy": "[6] Actual Local Tax Levy",
    "lfs_delta": "[7] Amt Over/(Under) LFS",
    "equalized_valuation": "[8] Equalized Property Valuation", 
    "district_income": "[9] Aggregate District Income"
}
ordered_cols = ["fiscal_year", "uncapped_aid", "s2_adjustment", "actual_net_payout", "adequacy_budget", "local_fair_share", "actual_tax_levy", "lfs_delta", "equalized_valuation", "district_income"]

# -----------------------------------------------------------------------------
# 4. RENDER THREE COHORT MATRIX TIERS
# -----------------------------------------------------------------------------
with tab1:
    # TIER 1: Individual District History Table
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

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # TIER 2: Cohort Peer Group Average Table
    st.markdown("#### 👥 Peer Group Benchmark Aggregator & Comparative Performance Matrix")
    st.caption(f"Displays mathematically computed multi-year group averages matching: **{sel_ld_filter}** | **{sel_type_filter}**")
    
    df_peer_pool = df_all_summary.copy()
    if sel_ld_filter != "All Districts":
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_ld"] == sel_ld_filter]
    if sel_type_filter != "All Types":
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_type"] == sel_type_filter]
        
    if not df_peer_pool.empty:
        df_grouped_averages = df_peer_pool.groupby("fiscal_year")[ordered_cols[1:]].mean().reset_index()
        df_peer_render = df_grouped_averages.sort_values("fiscal_year").copy()
        df_peer_render.rename(columns=rename_map, inplace=True)
        st.write(clean_html_currency_formatter(df_peer_render), unsafe_allow_html=True)

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # TIER 3: Absolute Statewide Averages Baseline Table
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