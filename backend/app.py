import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    # Added pagination/range logic
    headers_with_range = {**headers, "Range": "0-49999", "Prefer": "count=exact"}
    try:
        res = requests.get(f"{BASE_URL}/{table}?select=*", headers=headers_with_range)
        if res.status_code in [200, 206]:
            df = pd.DataFrame(res.json())
            df.columns = [str(c).lower().strip() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"Error fetching {table}: {e}")
    return pd.DataFrame()

# 2. LOAD DATA
df_aid = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_district_fte_summary")
df_map = fetch_table("legislative_mapping")
df_meta = fetch_table("district_metadata_mapping")

# 3. CLEANING
def clean(df):
    if df.empty: return df
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6)
    if "fiscal_year" in df.columns: 
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()
    return df

df_aid, df_enroll, df_map, df_meta = map(clean, [df_aid, df_enroll, df_map, df_meta])

# 4. SAFE MERGE
df_merged = df_aid.copy()
if not df_merged.empty:
    if not df_enroll.empty:
        df_merged = df_merged.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='outer')
    if not df_map.empty:
        df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    if not df_meta.empty:
        df_merged = df_merged.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')

# Initialize defaults if columns missing
for col in ['district_name', 'ld_display', 'district_type', 'county_name']:
    if col not in df_merged.columns: df_merged[col] = "Not Listed"
    df_merged[col] = df_merged[col].fillna("Not Listed")

# 5. UI
st.markdown("### 🏛️ NJ School Finance Platform")

if df_merged.empty:
    st.warning("No data found. Please check your Supabase API settings.")
else:
    c1, c2, c3, c4 = st.columns(4)
    sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().astype(str).tolist()))
    sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].unique().astype(str).tolist()))
    sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].unique().astype(str).tolist()))

    df_f = df_merged.copy()
    if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
    if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
    if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

    # Safe list generation
    district_list = sorted(df_f['district_name'].unique().astype(str).tolist()) if not df_f.empty else []
    sel_district = c4.selectbox("District:", ["Select..."] + district_list)

    if sel_district != "Select...":
        st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)