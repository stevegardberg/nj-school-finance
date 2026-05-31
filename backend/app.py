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
df_meta = fetch_table("district_metadata_mapping")
df_map = fetch_table("legislative_mapping")

# Function to clean names for a "Name Bridge"
def clean_name(val):
    return str(val).lower().replace("township", "twp").replace("town", "").strip()

# Normalize columns
for df in [df_aid, df_meta]:
    if not df.empty:
        df.columns = [str(c).lower().strip() for c in df.columns]
        # Create normalized name for bridging
        name_col = next((c for c in df.columns if 'district' in c and 'name' in c), None)
        if name_col:
            df['d_name_norm'] = df[name_col].apply(clean_name)

# 3. BRIDGE MERGE
# Attempt to merge on cds_code first, then bridge on name
df_merged = df_aid.copy()
if not df_meta.empty:
    # Try merging on normalized name to ensure we catch metadata
    df_merged = df_merged.merge(
        df_meta[['d_name_norm', 'district_type']], 
        on='d_name_norm', 
        how='left'
    )

# 4. COLUMN INITIALIZATION
for col in ['district_type', 'ld_display', 'district_name']:
    if col not in df_merged.columns:
        df_merged[col] = "Not Listed"
    else:
        df_merged[col] = df_merged[col].fillna("Not Listed")

# 5. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")
st.sidebar.write("Debug Types:", sorted(df_merged['district_type'].unique().tolist()))

c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted([t for t in df_merged['district_type'].unique() if t != "Not Listed"]))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged.get('county_name', pd.Series(['Unknown']*len(df_merged))).unique().tolist()))

# Filtering
df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f.get('district_name', pd.Series(['Unknown']*len(df_f))).unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)