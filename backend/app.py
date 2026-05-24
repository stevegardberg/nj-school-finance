import streamlit as st
import pandas as pd
import requests

# -----------------------------------------------------------------------------
# 1. LIVE SECURE DATABASE HANDSHAKE
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
SUPABASE_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary"

# Immutable NJ State County Code Signature Mapping Dictionary
NJ_COUNTY_PREFIXES = {
    "01": "Atlantic", "03": "Bergen", "05": "Burlington", "07": "Camden",
    "09": "Cape May", "11": "Cumberland", "13": "Essex", "15": "Gloucester",
    "17": "Hudson", "19": "Hunterdon", "21": "Mercer", "23": "Middlesex",
    "25": "Monmouth", "27": "Morris", "29": "Ocean", "31": "Passaic",
    "33": "Salem", "35": "Somerset", "37": "Sussex", "39": "Union", "41": "Warren"
}

def fetch_all_districts_metadata_live():
    """Queries the live table using multi-page offset streams to bypass server caps entirely."""
    all_records = []
    page = 0
    page_size = 1000  
    
    try:
        while True:
            offset = page * page_size
            url = f"{SUPABASE_URL}?select=cds_code,district_name&limit={page_size}&offset={offset}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                page_data = response.json()
                if not page_data:  
                    break
                all_records.extend(page_data)
                if len(page_data) < page_size:
                    break
                page += 1
            else:
                return {}, f"Server Pagination Halt (HTTP {response.status_code})"
        
        if not all_records:
            return {}, "Success (HTTP 200) | Database Connection Active, Table Currently Vacant."
        
        mapping = {}
        for row in all_records:
            d_name = str(row.get('district_name', '')).strip()
            c_code = str(row.get('cds_code', '')).strip().split('.')[0]
            
            if not d_name or d_name in ["None", ""]:
                continue
            if not c_code or c_code in ["None", ""]:
                continue
            
            padded_code = c_code.zfill(6)
            prefix = padded_code[:2]
            
            c_name = NJ_COUNTY_PREFIXES.get(prefix, f"Unassigned Prefix ({prefix})")
            
            if c_name not in mapping:
                mapping[c_name] = {}
            mapping[c_name][d_name] = c_code
            
        return mapping, f"Success (HTTP 200) | Formatted all {len(all_records)} historical data lines."
    except Exception as e:
        return {}, f"Network Infrastructure Timeout: {str(e)}"

@st.cache_data(ttl=5)
def fetch_live_multiyear_ledger(cds_code):
    """Queries live multi-year history lines for the selected district identifier."""
    try:
        url = f"{SUPABASE_URL}?cds_code=eq.{cds_code}&order=fiscal_year.asc"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()
    except Exception:
        pass
    return []

# -----------------------------------------------------------------------------
# 2. FULLY REACTIVE CONTROL PANEL NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🔍 Control Panel")

county_map, network_diagnostic_msg = fetch_all_districts_metadata_live()
all_counties = sorted(list(county_map.keys()))

if not all_counties:
    county_map = {"Staging Cluster": {"Upload Target Data Spreadsheet": "000000"}}
    all_counties = list(county_map.keys())

selected_county = st.sidebar.selectbox("Select County:", all_counties)

available_districts = county_map.get(selected_county, {})
sorted_districts = sorted(list(available_districts.keys()))

selected_district = st.sidebar.selectbox("Select School District:", sorted_districts)
current_cds = available_districts.get(selected_district, "")

# -----------------------------------------------------------------------------
# 3. EXECUTIVE PLATFORM LENS LAYOUT
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
st.markdown("**NJASBO 2026 Presentation Engine (Standardized Production Run)**")
st.info(f"**Jurisdiction:** {selected_district} ({selected_county} County) | **System CDS Primary Identifier Code:** {current_cds}")

tab1, tab2, tab3 = st.tabs([
    "⚖️ DATABASE VALIDATION MATRIX", 
    "📊 User Friendly Budget Approp Explorer",
    "🎯 Academic Return Matrix"
])

# -----------------------------------------------------------------------------
# 4. PURE REAL-TIME LOOKUP PRESENTATION ENGINE
# -----------------------------------------------------------------------------
with tab1:
    st.markdown("#### Audited Spreadsheet vs Cloud Database Cross-Examination")
    st.caption("This panel pulls raw multi-year records directly from your standardized Supabase ledger rows.")

    if current_cds and current_cds != "000000" and current_cds != "":
        raw_rows = fetch_live_multiyear_ledger(current_cds)
    else:
        raw_rows = []
    
    if raw_rows:
        df_ledger = pd.DataFrame(raw_rows)
        
        # Safe numeric casting to prevent formatting crash loops on empty/missing rows
        numeric_targets = ["uncapped_aid", "s2_adjustment", "actual_net_payout", "adequacy_budget", "local_fair_share", "equalized_valuation", "district_income", "actual_tax_levy"]
        for target in numeric_targets:
            if target in df_ledger.columns:
                df_ledger[target] = pd.to_numeric(df_ledger[target]).fillna(0.0)
            else:
                df_ledger[target] = 0.0

        # Calculate the dynamic Over/(Under) Local Fair Share vector on the fly
        df_ledger["lfs_delta"] = df_ledger["actual_tax_levy"] - df_ledger["local_fair_share"]
        
        # Comprehensive layout tracking array
        display_cols = [
            "fiscal_year", 
            "uncapped_aid", 
            "s2_adjustment",
            "actual_net_payout", 
            "adequacy_budget", 
            "local_fair_share", 
            "actual_tax_levy",
            "lfs_delta",
            "equalized_valuation", 
            "district_income"
        ]
        
        existing_cols = [col for col in display_cols if col in df_ledger.columns]
        df_render = df_ledger[existing_cols].copy()
        
        # Compute exact aggregate column summaries for the footer row target arrays
        total_s2_delta = df_render["s2_adjustment"].sum()
        total_lfs_delta = df_render["lfs_delta"].sum()

        # Build a fresh summary row dictionary structured cleanly to line up under headers
        summary_row = {col: "" for col in existing_cols}
        summary_row["fiscal_year"] = "<b>TOTAL SUMMARY</b>"
        summary_row["s2_adjustment"] = f"<b>{total_s2_delta}</b>"
        summary_row["lfs_delta"] = f"<b>{total_lfs_delta}</b>"
        
        # Append summary row to the bottom using Pandas concatenation path
        df_summary = pd.DataFrame([summary_row])
        df_final = pd.concat([df_render, df_summary], ignore_index=True)

        # Corporate Presentation Header Mapping Grid
        rename_map = {
            "fiscal_year": "Fiscal Year", 
            "uncapped_aid": "Uncapped SFRA Formula Target", 
            "s2_adjustment": "Legislative S2 Adjustment Delta",
            "actual_net_payout": "Actual Funding Net Payout", 
            "adequacy_budget": "Adequacy Budget Base",
            "local_fair_share": "Local Fair Share (LFS)",
            "actual_tax_levy": "Actual Local Tax Levy",
            "lfs_delta": "Amt Over/(Under) LFS",
            "equalized_valuation": "Equalized Property Valuation", 
            "district_income": "Aggregate District Income"
        }
        df_final.rename(columns=rename_map, inplace=True)
        
        # Clean currency formatting parser loop
        for col in df_final.columns:
            if col != "Fiscal Year":
                def format_cell(x):
                    if pd.isnull(x) or str(x).strip() == "":
                        return "$0.00"
                    val_str = str(x).replace("<b>", "").replace("</b>", "").strip()
                    if val_str == "":
                        return ""
                    try:
                        val_float = float(val_str)
                        formatted_val = f"${val_float:,.2f}" if val_float >= 0 else f"$-{abs(val_float):,.2f}"
                        if "<b>" in str(x):
                            return f"<b>{formatted_val}</b>"
                        return formatted_val
                    except ValueError:
                        return str(x)
                df_final[col] = df_final[col].apply(format_cell)
                
        st.write(df_final.to_html(index=False, escape=False), unsafe_allow_html=True)
    else:
        st.warning("⏳ Selecting a valid active lookup path to stream database rows...")

with tab2:
    st.markdown("#### UFB Appropriations Component Ledger")
    st.write("Dynamic lookups for user-friendly budget table segments will render here.")

with tab3:
    st.markdown("#### Return on Academic Investment Insights (ROAI)")
    st.info("💡 Next Move Integration: Once your Student Achievement data sheets are formatted to use your standardized 'cds_code' layout spine, we can join the rows here with zero coding retranslation needed.")

# -----------------------------------------------------------------------------
# 5. DIAGNOSTIC SYSTEM LOG SUMMARY
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🔍 System Audit Log Summary")
st.info(f"📡 **Network Pipeline Status:** {network_diagnostic_msg}")
if raw_rows:
    st.success(f"✅ **Database Pipeline Stable:** Loaded {len(raw_rows)} active rows for lookup key {current_cds}.")