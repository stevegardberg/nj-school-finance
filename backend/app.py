import streamlit as st
import pandas as pd
import numpy as np
import requests

# Set page configuration to maximum wide-mode for 12-column high spreadsheet density
st.set_page_config(layout="wide")

# Force-clear internal Streamlit memory buffers to guarantee fresh data streams
if 'initialized' not in st.session_state:
    st.cache_data.clear()
    st.session_state['initialized'] = True

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

def fetch_supabase_table_data(base_url):
    all_records = []
    page = 0
    page_size = 1000  
    try:
        while True:
            offset = page * page_size
            join_char = "&" if "?" in base_url else "?"
            url = f"{base_url}{join_char}limit={page_size}&offset={offset}"
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                page_data = response.json()
                if not page_data or len(page_data) == 0: break
                all_records.extend(page_data)
                if len(page_data) < page_size: break
                page += 1
            else: break
        return all_records
    except Exception: return all_records

def clean_html_currency_formatter(df):
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if col != "Fiscal Year":
            def format_cell(x):
                if pd.isnull(x) or str(x).strip() in ["", "nan", "None"]:
                    return "$0.00" if "%" not in col and "Rate" not in col else "0.00%" if "%" in col else "0.0000"
                raw_str = str(x).replace("<b>", "").replace("</b>", "").strip()
                if any(marker in raw_str for marker in ["$", "%", "TOTAL"]): return str(x)
                try:
                    val_float = float(raw_str)
                    if "%" in col: formatted_val = f"{val_float:+.2f}%" if val_float != 0 else "0.00%"
                    elif "Rate" in col: formatted_val = f"${val_float:,.4f}"
                    else: formatted_val = f"${val_float:,.2f}" if val_float >= 0 else f"$-{abs(val_float):,.2f}"
                    if "<b>" in str(x): return f"<b>{formatted_val}</b>"
                    return formatted_val
                except ValueError: return str(x)
            df_formatted[col] = df_formatted[col].apply(format_cell)
    return df_formatted.to_html(index=False, escape=False)

# -----------------------------------------------------------------------------
# 2. RUN DATA PIPELINE ACQUISITION
# -----------------------------------------------------------------------------
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
st.markdown("**NJASBO 2026 Presentation Engine (Relational Join Run)**")

raw_summary = fetch_supabase_table_data(SUPABASE_URL_SUMMARY)
raw_mapping = fetch_supabase_table_data(SUPABASE_URL_MAPPING)
raw_types = fetch_supabase_table_data(SUPABASE_URL_DIST_TYPE)
raw_revenue = fetch_supabase_table_data(SUPABASE_URL_REVENUE)

df_summary_base = pd.DataFrame(raw_summary) if raw_summary else pd.DataFrame(columns=["cds_code", "fiscal_year"])
df_mapping_base = pd.DataFrame(raw_mapping) if raw_mapping else pd.DataFrame(columns=["cds_code", "legislative_district"])
df_types_base = pd.DataFrame(raw_types) if raw_types else pd.DataFrame(columns=["cds_code", "district_name", "district_type"])

if df_summary_base.empty or df_types_base.empty:
    st.error("⏳ Critical Error: Could not establish connection to relational database tables.")
    st.stop()

def secure_string_normalize(series):
    return series.astype(str).str.split('.').str[0].str.strip().str.zfill(6).str[:6]

df_summary_base["join_key"] = secure_string_normalize(df_summary_base["cds_code"])
df_types_base["join_key"] = secure_string_normalize(df_types_base["cds_code"])
if not df_mapping_base.empty: df_mapping_base["join_key"] = secure_string_normalize(df_mapping_base["cds_code"])

df_summary_base["county_code"] = df_summary_base["join_key"].str[:2]
df_types_base["district_type"] = df_types_base["district_type"].astype(str).str.strip()
df_types_base["district_name"] = df_types_base["district_name"].astype(str).str.strip()
df_types_base["type_letter"] = df_types_base["district_type"].map(lambda x: x.split('.')[0].strip().upper() if '.' in x else x[:1].upper())

# Wealth data
df_all_rev = pd.DataFrame(raw_revenue) if raw_revenue else pd.DataFrame(columns=["cds_code", "fiscal_year", "line_no", "amount"])
if not df_all_rev.empty:
    df_all_rev["join_key"] = secure_string_normalize(df_all_rev["cds_code"])
    df_all_rev["fiscal_year"] = df_all_rev["fiscal_year"].astype(str).str.strip().str.upper()
    df_all_rev["amount"] = pd.to_numeric(df_all_rev["amount"]).fillna(0.0)
    df_val = df_all_rev[df_all_rev["line_no"].isin([40, "40"])].copy()
    df_inc = df_all_rev[df_all_rev["line_no"].isin([20, "20"])].copy()
    val_lookup = dict(zip(df_val["join_key"].str.cat(df_val["fiscal_year"], sep="_"), df_val["amount"]))
    inc_lookup = dict(zip(df_inc["join_key"].str.cat(df_inc["fiscal_year"], sep="_"), df_inc["amount"]))
else: val_lookup, inc_lookup = {}, {}

# -----------------------------------------------------------------------------
# 3. RELATIONAL JOIN EXECUTION
# -----------------------------------------------------------------------------
cols_to_purge = ["assigned_type", "assigned_type_label", "assigned_type_letter", "district_type", "type_letter", "district_name", "assigned_ld"]
for col in cols_to_purge:
    if col in df_summary_base.columns: df_summary_base.drop(columns=[col], inplace=True)

df_lookup_slice = df_types_base[["join_key", "district_name", "district_type", "type_letter"]].copy()
df_joined_master = pd.merge(df_summary_base, df_lookup_slice, on="join_key", how="left")

df_joined_master["district_type"] = df_joined_master["district_type"].fillna("B. K-8 / 0 - 400")
df_joined_master["type_letter"] = df_joined_master["type_letter"].fillna("B")
df_joined_master["district_name"] = df_joined_master["district_name"].fillna("Unknown District")

leg_dict = dict(zip(df_mapping_base["join_key"], df_mapping_base["legislative_district"].astype(str).str.strip())) if not df_mapping_base.empty else {}
df_joined_master["assigned_ld"] = df_joined_master["join_key"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned LD")

df_joined_master["fiscal_year"] = df_joined_master["fiscal_year"].astype(str).str.strip().str.upper()
df_joined_master["lookup_key"] = df_joined_master["join_key"].str.cat(df_joined_master["fiscal_year"], sep="_")
df_joined_master["equalized_valuation"] = df_joined_master["lookup_key"].map(lambda x: val_lookup.get(x, 0.0))
df_joined_master["district_income"] = df_joined_master["lookup_key"].map(lambda x: inc_lookup.get(x, 0.0))

for target in ["adequacy_budget", "uncapped_aid", "actual_net_payout", "s2_adjustment", "local_fair_share", "actual_tax_levy", "equalized_valuation", "district_income"]:
    df_joined_master[target] = pd.to_numeric(df_joined_master.get(target, 0.0)).fillna(0.0)

df_joined_master["lfs_delta"] = df_joined_master["actual_tax_levy"] - df_joined_master["local_fair_share"]
df_joined_master["assigned_county"] = df_joined_master["county_code"].map(lambda x: NJ_COUNTY_PREFIXES.get(x, "Unassigned"))

master_ld_options = sorted(list(set(df_joined_master[df_joined_master["assigned_ld"] != "Unassigned LD"]["assigned_ld"].dropna())))
master_type_options = sorted(list(set(df_joined_master["district_type"].dropna())))

# -----------------------------------------------------------------------------
# 4. HIERARCHICAL CASCADING FILTERS
# -----------------------------------------------------------------------------
with st.container():
    r_col1, r_col2 = st.columns([6, 1])
    with r_col2:
        if st.button("🔄 Reset All Filters", use_container_width=True): 
            st.cache_data.clear()
            st.rerun()

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1: sel_ld = st.selectbox("1️⃣ Legislative Filter:", ["All Legislative Districts"] + master_ld_options, index=0)
    with f_col2: sel_type_label = st.selectbox("2️⃣ District Type Filter:", ["All District Types"] + master_type_options, index=0)

    df_cascade = df_joined_master.copy()
    if sel_ld != "All Legislative Districts": df_cascade = df_cascade[df_cascade["assigned_ld"] == sel_ld]
    if sel_type_label != "All District Types":
        target_letter = sel_type_label.split('.')[0].strip().upper() if '.' in sel_type_label else sel_type_label[:1].upper()
        df_cascade = df_cascade[df_cascade["type_letter"] == target_letter]

    with f_col3:
        available_counties = sorted(list(set(df_cascade["assigned_county"].dropna())))
        if "Unassigned" in available_counties: available_counties.remove("Unassigned")
        sel_county = st.selectbox("3️⃣ Local County:", ["All Counties"] + available_counties, index=0)
    if sel_county != "All Counties": df_cascade = df_cascade[df_cascade["assigned_county"] == sel_county]

    with f_col4:
        available_towns = sorted(list(set(df_cascade["district_name"].dropna())))
        if "Unknown District" in available_towns: available_towns.remove("Unknown District")
        sel_district = st.selectbox("4️⃣ Target Local District:", ["Select a District..."] + available_towns, index=0)

tab1, tab2, tab3 = st.tabs(["⚖️ DATABASE VALIDATION MATRIX", "📊 User Friendly Budget Approp Explorer", "🎯 Academic Return Matrix"])

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
    df = df_group.sort_values("fiscal_year").copy()
    df["state_aid_pct_change"] = df["actual_net_payout"].pct_change().fillna(0.0) * 100.0
    df["tax_levy_pct_change"] = df["actual_tax_levy"].pct_change().fillna(0.0) * 100.0
    df["tax_rate_per_100"] = np.where(df["equalized_valuation"] > 0, (df["actual_tax_levy"] / df["equalized_valuation"]) * 100.0, 0.0)
    return df

with tab1:
    if sel_district and sel_district != "Select a District...":
        df_district_raw = df_joined_master[df_joined_master["district_name"] == sel_district].sort_values("fiscal_year").copy()
        if not df_district_raw.empty:
            df_render = calculate_advanced_metrics(df_district_raw)[ordered_display_cols].copy()
            st.write(clean_html_currency_formatter(df_render.rename(columns=rename_map)), unsafe_allow_html=True)
    else:
        st.info("💡 Adjust filters to display an individual district's ledger.")