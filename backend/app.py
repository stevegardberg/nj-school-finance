import streamlit as st
import pandas as pd
import requests

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
SUPABASE_PROJECT_ID = "exqwkzidanuywriatmhi"
URLS = {
    "Summary": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/state_aid_summary",
    "Mapping": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/legislative_mapping",
    "Types": f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/district_metadata_mapping"
}

@st.cache_data(ttl=3600)
def fetch_data(url):
    all_records = []
    page = 0
    while True:
        res = requests.get(f"{url}?limit=1000&offset={page*1000}", headers=headers)
        if res.status_code != 200 or not res.json(): break
        all_records.extend(res.json())
        page += 1
    return all_records

# 2. LOAD & MAP (Defensive logic)
df_all_summary = pd.DataFrame(fetch_data(URLS["Summary"]))
df_all_mapping = pd.DataFrame(fetch_data(URLS["Mapping"]))
df_all_types = pd.DataFrame(fetch_data(URLS["Types"]))

# Clean codes
df_all_summary["cds_code"] = df_all_summary["cds_code"].astype(str).str.zfill(6).str[:6]

# Create dictionaries only if data exists
leg_dict = dict(zip(df_all_mapping["cds_code"].astype(str).str.zfill(6), df_all_mapping["legislative_district"])) if not df_all_mapping.empty else {}
type_dict = dict(zip(df_all_types["cds_code"].astype(str).str.zfill(6), df_all_types["district_type"])) if not df_all_types.empty else {}

df_all_summary["assigned_ld"] = df_all_summary["cds_code"].map(lambda x: f"District {leg_dict.get(x)}" if leg_dict.get(x) else "Unassigned")
df_all_summary["assigned_type"] = df_all_summary["cds_code"].map(lambda x: type_dict.get(x, "Unassigned"))

# 3. UI
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
if st.button("🔄 Reset All"): st.rerun()

c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_all_summary["assigned_ld"].unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_all_summary["assigned_type"].unique().tolist()))

df_c = df_all_summary.copy()
if sel_ld != "All": df_c = df_c[df_c["assigned_ld"] == sel_ld]
if sel_type != "All": df_c = df_c[df_c["assigned_type"] == sel_type]

sel_district = c4.selectbox("4️⃣ Target District:", ["Select..."] + sorted(df_c["district_name"].dropna().unique().tolist()))

if sel_district != "Select...":
    st.dataframe(df_c[df_c["district_name"] == sel_district].sort_values("fiscal_year"), use_container_width=True)