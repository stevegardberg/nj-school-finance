import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# Set page configuration to maximum wide-mode for 12-column high spreadsheet density
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
SUPABASE_URL_DIST_TYPE = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
SUPABASE_URL_REVENUE = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/revenue"

NJ_COUNTY_PREFIXES = {
    "01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden",
    "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester",
    "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex",
    "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic",
    "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"
}

def fetch_supabase_table_data(base_url, force_refresh=False):
    """Paginates and extracts complete datasets safely with a cache-busting network token."""
    all_records = []
    page = 0
    page_size = 1000  
    
    # Add a dynamic timestamp parameter to force HTTP gateways to fetch live rows
    cache_buster = f"&cb={int(time.time())}" if force_refresh else ""
    
    try:
        while True:
            offset = page * page_size
            join_char = "&" if "?" in base_url else "?"
            url = f"{base_url}{join_char}limit={page_size}&offset={offset}{cache_buster}"
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
    """Transforms raw numeric dataframes into highly polished HTML tables with custom percentage formatting."""
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if col != "Fiscal Year":
            def format_cell(x):
                if pd.isnull(x) or str(x).strip() in ["", "nan", "None"]:
                    return "$0.00" if "%" not in col and "Rate" not in col else "0.00%" if "%" in col else "0.0000"
                
                raw_str = str(x).replace("<b>", "").replace("</b>", "").strip()
                if any(marker in raw_str for marker in ["$", "%", "TOTAL"]):
                    return str(x)
                    
                try:
                    val_float = float(raw_str)
                    if "%" in col:
                        formatted_val = f"{val_float:+.2f}%" if val_float != 0 else "0.00%"
                    elif "Rate" in col:
                        formatted_val = f"${val_float:,.4f}"
                    else:
                        formatted_val = f"${val_float:,.2f}" if val_float >= 0 else f"$-{abs(val_float):,.2f}"
                        
                    if "<b>" in str(x): return f"<b>{formatted_val}</b>"
                    return formatted_val
                except ValueError:
                    return str(x)
            df_formatted[col] = df_formatted[col].apply(format_cell)
    return df_formatted.to_html(index=False, escape=False)

# -----------------------------------------------------------------------------
# 2. RUN LIVE DATA FETCHING WITH EXPLICIT CACHE BUSTING
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
st.markdown("**NJASBO 2026 Presentation Engine (Live Cache-Busting Run)**")

# Force full live network downloads by passing True to our query utility
raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY, force_refresh=True)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING, force_refresh=True)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE, force_refresh=True)
raw_revenue = fetch_supabase_table_data(SUPABASE_URL_REVENUE, force_refresh=True)

if not raw_summary or not raw_types:
    st.error("⏳ Pipeline stalled. Key data fields returned empty arrays from the cloud data server.")
    st.stop()

df_summary_base = pd.DataFrame(raw_summary)
df_mapping_base = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_types_base = pd.DataFrame(raw_types)

# Clean and normalize join keys on the fly
df_summary_base["cds_code"] = df_summary_base["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]
if not df_mapping_base.empty: df_mapping_base["cds_code"] = df_mapping_base["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]
df_types_base["cds_code"] = df_types_base["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

# Prepare descriptive labels
df_types_base["district_type"] = df_types_base["district_type"].astype(str).str.strip()
df_types_base["type_letter"] = df_types_base["district_type"].map(lambda x: x.split('.')[0].strip().upper() if '.' in x else x[:1].upper())

# Extract wealth metrics from raw revenue data rows safely
df_all_rev = pd.DataFrame(raw_revenue) if raw_revenue else pd.DataFrame(columns=["cds_code", "fiscal_year", "line_no", "amount"])
if not df_all_rev.empty:
    df_all_rev["cds_code"] = df_all_rev["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]
    df_all_rev["fiscal_year"] = df_all_rev["fiscal_year"].astype(str).str.strip().str.upper()
    df_all_rev["amount"] = pd.to_numeric(df_all_rev["amount"]).fillna(0.0)
    
    df_val = df_all_rev[df_all_rev["line_no"].isin([40, "40"])].copy()
    df_inc = df_all_rev[df_all_rev["line_no"].isin([20, "20"])].copy()
    
    val_lookup = dict(zip(df_val["cds_code"].str.cat(df_val["fiscal_year"], sep="_"), df_val["amount"]))
    inc_lookup = dict(zip(df_inc["cds_code"].str.cat(df_inc["fiscal_year"], sep="_"), df_inc["amount"]))
else:
    val_lookup, inc_lookup = {}, {}

# -----------------------------------------------------------------------------
# 3. COMBINE DATASETS USING RESILIENT CLIENT-SIDE LEFT JOIN
# -----------------------------------------------------------------------------
cols_to_drop = ["assigned_type", "assigned_type_label", "assigned_type_letter", "district_type", "type_letter", "district_name"]
df_summary_base.drop(columns=[c for c in cols_to_drop if c in df_summary_base.columns], inplace=True)

# Merge tables on clean 6-digit text codes
df_joined_master = pd.merge(df_summary_base, df_types_base, on="cds_code", how="left")

# Fallback defaults if a record from the ledger falls outside our clean map boundaries
df_joined_master["district_type"] = df_joined_master["district_type"].fillna("B. K-8 / 0 - 400")
df_joined_master["type_letter"] = df_joined_master["type_letter"].fillna("B")

# Re-link legislative maps
leg_dict = dict(zip(df_mapping_base["cds_code"], df_mapping_base["legislative_district"].astype(str).str.strip())) if not df_mapping_base.empty else {}
df_joined_master["assigned_ld"] = df_joined_master["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned LD")

df_joined_master["fiscal_year"] = df_joined_master["fiscal_year"].astype(str).str.strip().str.upper()
df_joined_master["lookup_key"] = df_joined_master["cds_code"].str.cat(df_joined_master["fiscal_year"], sep="_")
df_joined_master["equalized_valuation"] = df_joined_master["lookup_key"].map(lambda x: val_lookup.get(x, 0.0))
df_joined_master["district_income"] = df_joined_master["lookup_key"].map(lambda x: inc_lookup.get(x, 0.0))

# Fast-cast financial numbers safely
for target in ["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]:
    df_joined_master[target] = pd.to_numeric(df_joined_master.get(target, 0.0)).fillna(0.0)

df_joined_master["lfs_delta"] = df_joined_master["actual_tax_levy"] - df_joined_master["local_fair_share"]
df_joined_master["assigned_county"] = df_joined_master["cds_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x[:2], "Unassigned"))

# Generate static dropdown choices directly from verified database outputs
master_ld_options = sorted(list(set(df_joined_master[df_joined_master["assigned_ld"] != "Unassigned LD"]["assigned_ld"].dropna())))
master_type_options = sorted(list(set(df_types_base["district_type"].dropna())))

# -----------------------------------------------------------------------------
# 4. ADVANCED HIERARCHICAL CASCADING HEADER FILTERS
# -----------------------------------------------------------------------------
with st.container():
    r_col1, r_col2 = st.columns([6, 1])
    with r_col2:
        if st.button("🔄 Reset All Filters", use_container_width=True): st.rerun()

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    
    with f_col1:
        sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options, index=0)
    with f_col2:
        sel_type_label = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options, index=0)

    # Filter our active data frame based on user selection
    df_cascade = df_joined_master.copy()
    
    if sel_ld != "All Legislative Districts":
        df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
        
    if sel_type_label != "All District Types":
        target_letter = sel_type_label.split('.')[0].strip().upper() if '.' in sel_type_label else sel_type_label[:1].upper()
        df_cascade = df_cascade[df_cascade["type_letter"] == target_letter]

    with f_col3:
        available_counties = sorted(list(set(df_cascade["assigned_county"].dropna())))
        if "Unassigned" in available_counties: available_counties.remove("Unassigned")
        sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + available_counties, index=0)

    if sel_county != "All Counties":
        df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

    with f_col4:
        available_towns = sorted(list(set(df_cascade["district_name"].dropna())))
        sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + available_towns, index=0)

    st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

# -----------------------------------------------------------------------------
# 5. STRUCTURAL NARRATIVE COLUMN FORMAT MAPPING KEYS
# -----------------------------------------------------------------------------
rename_map = {
    "fiscal_year": "Fiscal Year",
    "adequacy_budget": "[1] Adequacy Budget Base",
    "uncapped_aid": "[2] Uncapped SFRA Formula Target",
    "actual_net_payout": "[3] Actual State Aid",
    "state_aid_pct_change": "[4] State Aid YoY % Change",
    "s2_adjustment": "[5] Legislative S2 Adjustment Delta",
    "local_fair_share": "[6] Local Fair Share (LFS)",
    "actual_tax_levy": "[7] Actual Local Tax Levy",
    "tax_levy_pct_change": "[8] Tax Levy YoY % Change",
    "lfs_delta": "[9] Amt Over/(Under) LFS",
    "equalized_valuation": "[10] Equalized Property Valuation",
    "tax_rate_per_100": "[11] Tax Rate per $100 Valuation",
    "district_income": "[12] Aggregate District Income"
}
ordered_display_cols = [
    "fiscal_year", "adequacy_budget", "uncapped_aid", "actual_net_payout", "state_aid_pct_change",
    "s2_adjustment", "local_fair_share", "actual_tax_levy", "tax_levy_pct_change", "lfs_delta",
    "equalized_valuation", "tax_rate_per_100", "district_income"
]

def calculate_advanced_metrics(df_group):
    """Computes percentage changes and tax levy rate modifiers safely across year-ordered rows."""
    df = df_group.sort_values("fiscal_year").copy()
    df["state_aid_pct_change"] = df["actual_net_payout"].pct_change().fillna(0.0) * 100.0
    df["tax_levy_pct_change"] = df["actual_tax_levy"].pct_change().fillna(0.0) * 100.0
    df["tax_rate_per_100"] = np.where(df["equalized_valuation"] > 0, (df["actual_tax_levy"] / df["equalized_valuation"]) * 100.0, 0.0)
    return df

# -----------------------------------------------------------------------------
# 6. RENDER PERFORMANCE GRIDS
# -----------------------------------------------------------------------------
with tab1:
    current_active_ld, current_active_type_letter = None, None

    # --- TIER 1: TARGET DISTRICT LEDGER ---
    if sel_district and sel_district != "Select a District...":
        st.markdown(f"#### 📍 Target District Multi-Year Ledger — {sel_district}")
        df_district_raw = df_joined_master[df_joined_master["district_name"] == sel_district].copy()
        
        if not df_district_raw.empty:
            df_processed = calculate_advanced_metrics(df_district_raw)
            df_render = df_processed[ordered_display_cols].copy()
            
            tot_s2 = df_render["s2_adjustment"].sum()
            tot_lfs = df_render["lfs_delta"].sum()
            
            sum_row = {col: "" for col in df_render.columns}
            sum_row["fiscal_year"] = "<b>TOTAL SUMMARY</b>"
            sum_row["s2_adjustment"] = f"<b>{tot_s2}</b>"
            sum_row["lfs_delta"] = f"<b>{tot_lfs}</b>"
            
            df_final_matrix = pd.concat([df_render, pd.DataFrame([sum_row])], ignore_index=True)
            df_final_matrix.rename(columns=rename_map, inplace=True)
            st.write(clean_html_currency_formatter(df_final_matrix), unsafe_allow_html=True)
            
            current_active_ld = df_district_raw["assigned_ld"].iloc[0]
            current_active_type_letter = df_district_raw["type_letter"].iloc[0]
    else:
        st.info("💡 Select a local target district above to view the multi-year calculation ledger.")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- TIER 2: COHORT PEER GROUP AVERAGE ---
    st.markdown("#### 👥 Peer Group Benchmark Aggregator & Comparative Performance Matrix")
    target_peer_ld = sel_ld if sel_ld != "All Legislative Districts" else (current_active_ld if current_active_ld else "All Legislative Districts")
    
    if sel_type_label != "All District Types":
        target_peer_letter = sel_type_label.split('.')[0].strip().upper() if '.' in sel_type_label else sel_type_label[:1].upper()
    else:
        target_peer_letter = current_active_type_letter if current_active_type_letter else "B"
        
    st.caption(f"Displays mathematically computed group averages matching: **{target_peer_ld}** | Cohort Letter: **{target_peer_letter}**")
    
    df_peer_pool = df_joined_master.copy()
    if target_peer_ld != "All Legislative Districts": 
        df_peer_pool = df_peer_pool[df_peer_pool["assigned_ld"] == target_peer_ld]
    if target_peer_letter: 
        df_peer_pool = df_peer_pool[df_peer_pool["type_letter"] == target_peer_letter]
        
    if not df_peer_pool.empty:
        df_peer_yearly = df_peer_pool.groupby("fiscal_year")[["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income", "lfs_delta"]].mean().reset_index()
        df_peer_processed = calculate_advanced_metrics(df_peer_yearly)
        df_peer_render = df_peer_processed[ordered_display_cols].copy()
        
        tot_peer_s2 = df_peer_render["s2_adjustment"].sum()
        tot_peer_lfs = df_peer_render["lfs_delta"].sum()
        
        peer_sum_row = {col: "" for col in df_peer_render.columns}
        peer_sum_row["fiscal_year"] = "<b>TOTAL SUMMARY</b>"
        peer_sum_row["s2_adjustment"] = f"<b>{tot_peer_s2}</b>"
        peer_sum_row["lfs_delta"] = f"<b>{tot_peer_lfs}</b>"
        
        df_peer_final = pd.concat([df_peer_render, pd.DataFrame([peer_sum_row])], ignore_index=True)
        df_peer_final.rename(columns=rename_map, inplace=True)
        st.write(clean_html_currency_formatter(df_peer_final), unsafe_allow_html=True)

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- TIER 3: STATE-WIDE MACRO BASELINE ---
    st.markdown("#### 🌐 State-Wide Structural Averages Baseline")
    st.caption("Displays the macro baseline average across all combined public school systems in New Jersey per year.")
    
    if not df_joined_master.empty:
        df_state_yearly = df_joined_master.groupby("fiscal_year")[["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income", "lfs_delta"]].mean().reset_index()
        df_state_processed = calculate_advanced_metrics(df_state_yearly)
        df_state_render = df_state_processed[ordered_display_cols].copy()
        
        tot_state_s2 = df_state_render["s2_adjustment"].sum()
        tot_state_lfs = df_state_render["lfs_delta"].sum()
        
        state_sum_row = {col: "" for col in df_state_render.columns}
        state_sum_row["fiscal_year"] = "<b>TOTAL SUMMARY</b>"
        state_sum_row["s2_adjustment"] = f"<b>{tot_state_s2}</b>"
        state_sum_row["lfs_delta"] = f"<b>{tot_state_lfs}</b>"
        
        df_state_final = pd.concat([df_state_render, pd.DataFrame([state_sum_row])], ignore_index=True)
        df_state_final.rename(columns=rename_map, inplace=True)
        st.write(clean_html_currency_formatter(df_state_final), unsafe_allow_html=True)

with tab2: st.markdown("#### UFB Appropriations Component Ledger")
with tab3: st.markdown("#### Return on Academic Investment Insights (ROAI)")