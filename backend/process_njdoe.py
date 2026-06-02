@st.cache_data(ttl=3600)
def get_data():
    df_sum = fetch_table("state_aid_summary")
    df_map = fetch_table("legislative_mapping")
    # Point to the correct table identified in your schema audit
    df_types = fetch_table("district_metadata_mapping") 

    for df in [df_sum, df_map, df_types]:
        if "cds_code" in df.columns:
            df["cds_code"] = df["cds_code"].astype(str).str.zfill(6)

    # Merge using the correct columns found in your schema
    df = df_sum.merge(df_map[['cds_code', 'ld_display']], on='cds_code', how='left')
    df = df.merge(df_types[['cds_code', 'district_type']], on='cds_code', how='left')
    
    return df