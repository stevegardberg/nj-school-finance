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

# 2. LOAD & DYNAMIC NORMALIZATION
df_aid = fetch_table("state_aid_summary")
df_meta = fetch_table("district_metadata_mapping")
df_map = fetch_table("legislative_mapping")

def normalize_df(df):
    """Finds the name column dynamically and creates a norm key."""
    df.columns = [str(c).lower().strip() for c in df.columns]
    # Look for any column that contains 'district' and 'name'
    name_col = next((c for c in df.columns if 'district' in c and 'name' in c), None)
    if name_col:
        df['d_name_norm'] = df[name_col].astype(str).str.lower().str.strip()
    return df

df_aid = normalize_df(df_aid)
df_meta = normalize_df(df_meta)

# 3. BRIDGE MERGE (Only if norm columns exist)
df_merged = df_aid.copy()
if 'd_name_norm' in df_meta.columns and 'd_name_norm' in df_merged.columns:
    df_merged = df_merged.merge(df_meta[['d_name_norm', 'district_type']], on='d_name_norm', how='left')
else:
    df_merged['district_type'] = "Not Listed"

# 4. UI
st.markdown("### 🏛️ NJ School Finance Intelligence Platform")

# Fill missing columns for UI
df_merged['district_type'] = df_merged.get('district_type', 'Not Listed').fillna('Not Listed')
df_merged['ld_display'] = df_merged.get('ld_display', 'Not Listed').fillna('Not Listed')

c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged.get('county_name', pd.Series(['Unknown']*len(df_merged))).unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]

district_list = sorted(df_f.get('district_name', pd.Series(['Unknown']*len(df_f))).unique().tolist())
sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + district_list)

if sel_district != "Select...":
    st.dataframe(df_merged[df_merged['district_name'] == sel_district], use_container_width=True)