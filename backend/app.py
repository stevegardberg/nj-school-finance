import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    try:
        res = requests.get(f"{BASE_URL}/{table}?select=*", headers=headers)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            df.columns = [str(c).lower().strip() for c in df.columns]
            return df
    except: pass
    return pd.DataFrame()

# 2. LOAD DATA
df_aid = fetch_table("state_aid_summary")
df_enroll = fetch_table("v_district_fte_summary")
df_map = fetch_table("legislative_mapping")
df_meta = fetch_table("district_metadata_mapping")

# 3. CLEANING
def clean(df):
    if "cds_code" in df.columns: 
        df["cds_code"] = df["cds_code"].astype(str).str.split('.').str[0].str.strip().str.zfill(6)
    if "fiscal_year" in df.columns: 
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()
    return df

df_aid = clean(df_aid)
df_enroll = clean(df_enroll)
df_map = clean(df_map)
df_meta = clean(df_meta)

# 4. SAFE MERGE (Handles missing tables/columns gracefully)
df_merged = df_aid.copy()

# Merge Enrollment
if not df_enroll.empty and 'fiscal_year' in df_enroll.columns:
    df_merged = df_merged.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='outer')

# Merge Mapping (Only if valid)
if not df_map.empty and 'ld_display' in df_map.columns:
    df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
else:
    df_merged['ld_display'] = "Not Listed"

# Merge Metadata (Only if valid)
if not df_meta.empty and 'district_type' in df_meta.columns:
    df_merged = df_merged.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')
else:
    df_merged['district_type'] = "Not Listed"

# FILL GAPS
df_merged['district_name'] = df_merged['district_name'].fillna("Unknown")
df_merged['ld_display'] = df_merged['ld_display'].fillna("Not Listed")
df_merged['district_type'] = df_merged['district_type'].fillna("Not Listed")
df_merged['county_name'] = df_merged['county_name'].fillna("Unknown")

# 5. UI
st.markdown("### 🏛️ NJ School Finance Platform")

# Debugging
st.sidebar.write(f"Raw Aid Rows: {len(df_aid)}")
st.sidebar.write(f"Boonton Raw Check: {len(df_aid[df_aid['district_name'].str.contains('Boonton', na=False, case=False)])}")

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().astype(str).tolist()))
sel_type = c2.selectbox("District Type:", ["All"] + sorted(df_merged['district_type'].unique().astype(str).tolist()))
sel_county = c3.selectbox("County:", ["All"] + sorted(df_merged['county_name'].unique().astype(str).tolist()))

# Filter
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

district_list = sorted(df_f['district_name'].unique().astype(str).tolist())
sel_district = c4.selectbox("District:", ["Select..."] + district_list)

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)