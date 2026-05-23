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
    """Queries the live table and extracts geography with absolute whitespace immunity."""
    try:
        # Request only what we need to minimize network payload size
        url = f"{SUPABASE_URL}?select=cds_code,district_name"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if not data:
                return {}, "Success (HTTP 200) | Database Connection Active, Table Currently Vacant."
            
            mapping = {}
            for row in data:
                d_name = str(row.get('district_name', '')).strip()
                # Crucial Fix: Cast to string, strip whitespaces, remove decimals if Excel forced float conversion
                c_code = str(row.get('cds_code', '')).strip().split('.')[0]
                
                if not d_name or d_name in ["None", ""]:
                    continue
                if not c_code or c_code in ["None", ""]:
                    continue
                
                # Force clean zero-padding up to 6 digits regardless of input state
                padded_code = c_code.zfill(6)
                prefix = padded_code[:2]
                
                # Match against our geographic dictionary, defaulting gracefully
                c_name = NJ_COUNTY_PREFIXES.get(prefix, f"Unassigned Prefix ({prefix})")
                
                if c_name not in mapping:
                    mapping[c_name] = {}
                mapping[c_name][d_name] = c_code
                
            return mapping, "Success (HTTP 200) | Active Records Streamed Seamlessly."
        else:
            return {}, f"Server Rejected Authorization (HTTP {response.status_code})"
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
        display_cols = ["fiscal_year", "actual_state_aid", "adequacy_budget", "uncapped_aid", "local_fair_share", "equalized_valuation", "district_income"]
        existing_cols = [col for col in display_cols if col in df_ledger.columns]
        df_render = df_ledger[existing_cols].copy()
        
        rename_map = {
            "fiscal_year": "Fiscal Year", "actual_state_aid": "Actual K-12 State Aid", "adequacy_budget": "Adequacy Budget Base",
            "uncapped_aid": "Uncapped Aid Formulation", "local_fair_share": "Local Fair Share (LFS)",
            "equalized_valuation": "Equalized Property Valuation", "district_income": "Aggregate District Income"
        }
        df_render.rename(columns=rename_map, inplace=True)
        
        for col in df_render.columns:
            if col != "Fiscal Year":
                df_render[col] = df_render[col].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        st.write(df_render.to_html(index=False, escape=False), unsafe_allow_html=True)
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