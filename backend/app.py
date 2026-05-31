import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_table(table):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{BASE_URL}/{table}?select=*&limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return pd.DataFrame(all_records)

# 2. LOAD & CLEAN
df_aid = fetch_table("state_aid_summary")
df_map = fetch_table("legislative_mapping")
df_meta = fetch_table("district_metadata_mapping")
df_enroll = fetch_table("v_district_fte_summary")

def standardize_cds(val):
    """Force every code to be a 6-digit string."""
    s = str(val).split('.')[0].strip()
    return s.zfill(6)

for df in [df_aid, df_map, df_meta, df_enroll]:
    if not df.empty:
        df.columns = [str(c).lower().strip() for c in df.columns]
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].apply(standardize_cds)
        if "fiscal_year" in df.columns:
            df["fiscal_year"] = df["fiscal_year"].astype(str).str.strip()

# 3. MERGE
df_merged = df_aid.copy()
if not df_enroll.empty:
    df_merged = df_merged.merge(df_enroll, on=['cds_code', 'fiscal_year'], how='left')
if not df_map.empty:
    df_merged = df_merged.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
if not df_meta.empty:
    df_merged = df_merged.merge(df_meta[['cds_code', 'district_type']], on='cds_code', how='left')

# FILL & CLEAN
for col in ['district_name', 'ld_display', 'district_type', 'county_name']:
    df_merged[col] = df_merged.get(col, "Not Listed").astype(str).str.strip().replace("nan", "Not Listed").fillna("Not Listed")

# 4. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")
st.sidebar.write(f"Types Found: {sorted(df_merged['district_type'].unique().tolist())}")

c1, c2, c3, c4 = st.columns(4)

# Filter unique types, removing 'Not Listed' for the dropdown
unique_types = sorted([t for t in df_merged['district_type'].unique() if t != "Not Listed"])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + unique_types)
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)