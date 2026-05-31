import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

# 1. SETUP
headers = {"apikey": st.secrets["headers"]["apikey"], "Authorization": st.secrets["headers"]["Authorization"]}
BASE_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"

@st.cache_data(ttl=3600)
def fetch_all_data():
    # Helper to paginate all tables
    def get_table(table):
        all_records = []
        page = 0
        while True:
            res = requests.get(f"{BASE_URL}/{table}?select=*&limit=1000&offset={page*1000}", headers=headers)
            if res.status_code != 200 or not res.json(): break
            all_records.extend(res.json())
            page += 1
        return pd.DataFrame(all_records)

    return get_table("state_aid_summary"), get_table("legislative_mapping"), \
           get_table("vw_district_cohorts"), get_table("enrollment_master")

# 2. LOAD & AGGREGATE
df_sum, df_map, df_types, df_enroll = fetch_all_data()

# Clean and Calculate Enrollment
df_enroll.columns = [str(c).lower().strip() for c in df_enroll.columns]
valid_lines = ['C1', 'C2', 'D1', 'D2', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '19', '20', '21', '37', '38']
df_enroll = df_enroll[df_enroll['grade_level'].isin(valid_lines)].copy()
for col in ['onroll_ft', 'onroll_st']:
    df_enroll[col] = pd.to_numeric(df_enroll[col], errors='coerce').fillna(0)

df_enroll['fte'] = df_enroll['onroll_ft'] + (df_enroll['onroll_st'] * 0.5)
df_total_enroll = df_enroll.groupby(['cds_code', 'fiscal_year'])['fte'].sum().reset_index().rename(columns={'fte': 'resident_enrollment'})

# Merge and Calculate Metrics
df_merged = df_sum.merge(df_total_enroll, on=['cds_code', 'fiscal_year'], how='left') \
                  .merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left') \
                  .merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')

def add_metrics(df):
    df = df.sort_values(['district_name', 'fiscal_year'])
    df['Pct_Change_Aid'] = df.groupby('district_name')['actual_state_aid'].pct_change().fillna(0)
    df['Pct_Change_Levy'] = df.groupby('district_name')['actual_tax_levy'].pct_change().fillna(0)
    df['Over_Under_Funded'] = df['actual_state_aid'] - df['uncapped_aid']
    df['Over_Under_LFS'] = df['actual_tax_levy'] - df['local_fair_share']
    df['Tax_Levy_per_100'] = (df['actual_tax_levy'] / df['equalized_valuation'].replace(0, 1)) * 100
    return df

df_merged = add_metrics(df_merged)

# 3. UI LAYOUT
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
c1, c2, c3, c4 = st.columns(4)
sel_ld = c1.selectbox("1️⃣ Legislative:", ["All"] + sorted(df_merged['ld_display'].dropna().unique().tolist()))
sel_type = c2.selectbox("2️⃣ District Type:", ["All"] + sorted(df_merged['district_type'].dropna().unique().tolist()))
sel_county = c3.selectbox("3️⃣ County:", ["All"] + sorted(df_merged['county_name'].dropna().unique().tolist()))

df_f = df_merged.copy()
if sel_ld != "All": df_f = df_f[df_f['ld_display'] == sel_ld]
if sel_type != "All": df_f = df_f[df_f['district_type'] == sel_type]
if sel_county != "All": df_f = df_f[df_f['county_name'] == sel_county]

sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + sorted(df_f['district_name'].dropna().unique().tolist()))

if sel_district != "Select...":
    target_data = df_f[df_f['district_name'] == sel_district]
    st.subheader(f"📍 Financial Ledger: {sel_district}")
    st.dataframe(get_formatted_matrix(target_data), use_container_width=True, hide_index=True)
    
    # Peers Logic
    for name, group_col, val in [("Legislative District", 'ld_display', target_data['ld_display'].iloc[0]), 
                                 ("District Type", 'district_type', target_data['district_type'].iloc[0])]:
        if val:
            st.markdown("---")
            st.subheader(f"🏛️ {name} Average: {val}")
            peers = df_merged[df_merged[group_col] == val].copy()
            avg = add_metrics(peers).groupby('fiscal_year').mean(numeric_only=True).reset_index()
            st.dataframe(get_formatted_matrix(avg[avg['fiscal_year'].isin(target_data['fiscal_year'].unique())]), use_container_width=True, hide_index=True)