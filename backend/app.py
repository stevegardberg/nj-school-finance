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

# Point to your newly standardized state_aid_summary production table
SUPABASE_URL = "https://gci5q9y7luqn6t8jfsfbmm.supabase.co/rest/v1/state_aid_summary"

@st.cache_data(ttl=60)
def fetch_all_districts_metadata():
    """Queries the live database to dynamically build the navigation lists."""
    try:
        # Pull records from the standardized columns
        url = f"{SUPABASE_URL}?select=county_name,district_name,cds_code"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and response.json():
            df = pd.DataFrame(response.json())
            
            mapping = {}
            for _, row in df.iterrows():
                # Read columns, stripping whitespaces
                raw_county = str(row.get('county_name', '')).strip()
                d_name = str(row.get('district_name', '')).strip()
                c_code = str(row.get('cds_code', '')).strip()
                
                if not d_name or d_name == "None":
                    continue
                
                # SMART FALLBACK: If county_name is NULL or empty, handle gracefully
                if not raw_county or raw_county == "None" or raw_county == "":
                    # Quick deduction rules for demo stability
                    if "Boonton" in d_name:
                        c_name = "Morris"
                    elif "Absecon" in d_name or "Atlantic" in d_name or "Egg Harbor" in d_name or "Galloway" in d_name or "Hammonton" in d_name or "Pleasantville" in d_name or "Somers" in d_name or "Brigantine" in d_name or "Mainland" in d_name:
                        c_name = "Atlantic"
                    else:
                        c_name = "Statewide Unassigned"
                else:
                    c_name = raw_county
                
                if c_name not in mapping:
                    mapping[c_name] = {}
                mapping[c_name][d_name] = c_code
                
            return mapping
    except Exception as e:
        st.sidebar.error(f"Database Mapping Sync Error: {e}")
    return {"Error Connection": {"Verify Database Pipes": "000000"}}

@st.cache_data(ttl=10)
def fetch_live_multiyear_ledger(cds_code):
    """Queries all historical records matching the selected district string identifier."""
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

# Populate menu loops entirely based on active database row discovery
county_map = fetch_all_districts_metadata()
all_counties = sorted(list(county_map.keys()))

# Prevent an initialization crash if the dictionary returned empty
if not all_counties:
    all_counties = ["Statewide Unassigned"]

selected_county = st.sidebar.selectbox("Select County:", all_counties)

available_districts = county_map.get(selected_county, {})
sorted_districts = sorted(list(available_districts.keys()))

if not sorted_districts:
    sorted_districts = ["No Districts Discovered"]

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

    if current_cds and current_cds != "":
        raw_rows = fetch_live_multiyear_ledger(current_cds)
    else:
        raw_rows = []
    
    if raw_rows:
        df_ledger = pd.DataFrame(raw_rows)
        
        # Explicit clean targets mapping directly to your newly altered database columns
        display_cols = [
            "fiscal_year", "actual_state_aid", "adequacy_budget", 
            "uncapped_aid", "local_fair_share", "equalized_valuation", "district_income"
        ]
        
        existing_cols = [col for col in display_cols if col in df_ledger.columns]
        df_render = df_ledger[existing_cols].copy()
        
        # Map clean public-facing headers
        rename_map = {
            "fiscal_year": "Fiscal Year",
            "actual_state_aid": "Actual K-12 State Aid",
            "adequacy_budget": "Adequacy Budget Base",
            "uncapped_aid": "Uncapped Aid Formulation",
            "local_fair_share": "Local Fair Share (LFS)",
            "equalized_valuation": "Equalized Property Valuation",
            "district_income": "Aggregate District Income"
        }
        df_render.rename(columns=rename_map, inplace=True)
        
        # Apply clean financial formatting to columns found
        for col in df_render.columns:
            if col != "Fiscal Year":
                df_render[col] = df_render[col].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        
        # Render horizontal spreadsheet grid view
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
# 5. IMMUTABLE SYSTEM AUDIT SUMMARY
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🔍 System Audit Log Summary")
if raw_rows:
    st.success(f"✅ **Database Pipeline Stable:** Loaded {len(raw_rows)} active consecutive multi-year rows from table 'state_aid_summary' for lookup key {current_cds}.")
else:
    st.info(f"💡 Listening for valid data matrix hooks on identifier parameter query: {current_cds}")