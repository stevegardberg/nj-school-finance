import pandas as pd
import streamlit as st
import requests
import urllib.parse
st.set_page_config(page_title='NJ School Finance Intelligence Platform', page_icon='🏛️', layout='wide', initial_sidebar_state='expanded')
st.markdown('<style>.metric-card { background-color: #f8f9fa; border-left: 5px solid #1e3a8a; padding: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); } .banner-box { background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px; } .insight-card { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px; border-radius: 8px; margin-bottom: 15px; }</style>', unsafe_allow_html=True)
DB_URL = 'https://exqwkzidanuywriatmhi.supabase.co/rest/v1'
HEADERS = {'apikey': 'sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y', 'Authorization': 'Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y'}
@st.cache_data
def fetch_legislative_ledger():
    r = requests.get(f'{DB_URL}/legislative_mapping?select=*', headers=HEADERS)
    return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
@st.cache_data
def fetch_district_metrics(cds_padded, cds_raw):
    query = f'or=(cds.eq.{cds_padded},cds.eq.{cds_raw})'
    enroll = requests.get(f"{DB_URL}/enrollment?{query}", headers=HEADERS).json()
    costs  = requests.get(f"{DB_URL}/pupil_costs?{query}", headers=HEADERS).json()
    recap  = requests.get(f"{DB_URL}/recap_balance?{query}", headers=HEADERS).json()
    state_aid_url = f"{DB_URL}/{urllib.parse.quote('State Aid Summary')}?or=(CDS_Code.eq.{cds_padded},CDS_Code.eq.{cds_raw})"
    state_aid = requests.get(state_aid_url, headers=HEADERS).json()
    revenue_url = f"{DB_URL}/revenue?{query}"
    rev_data = requests.get(revenue_url, headers=HEADERS).json()
    return enroll, costs, recap, state_aid, rev_data
@st.cache_data
def fetch_all_pupil_costs():
    r = requests.get(f'{DB_URL}/pupil_costs?select=cds,line_desc,amount', headers=HEADERS)
    return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
@st.cache_data
def fetch_global_adequacy_ledger():
    state_aid_url = f"{DB_URL}/{urllib.parse.quote('State Aid Summary')}?select=*"
    r = requests.get(state_aid_url, headers=HEADERS)
    return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
df_maps = fetch_legislative_ledger()
df_global_aid = fetch_global_adequacy_ledger()
st.sidebar.markdown('## 🔍 Control Panel')
if df_maps.empty:
    st.error('❌ Critical Error: Unable to settle connection with cloud data ledger.')
else:
    counties = sorted(df_maps['county_name'].dropna().unique())
    selected_county = st.sidebar.selectbox('Select County:', ['All'] + counties)
    filtered_df = df_maps if selected_county == 'All' else df_maps[df_maps['county_name'] == selected_county]
    districts = sorted(filtered_df['district_name'].dropna().unique())
    selected_district = st.sidebar.selectbox('Select School District:', districts)
    meta = df_maps[df_maps['district_name'] == selected_district].iloc[0]
    raw_cds = str(meta['cds']).strip()
    cds_padded = raw_cds.zfill(9)[:6] if len(raw_cds) >= 8 else raw_cds.zfill(6)
    cds_raw = str(int(cds_padded))
    leg_dist = int(meta['legislative_district'])
    enroll_data, costs_data, recap_data, state_aid_data, revenue_data = fetch_district_metrics(cds_padded, cds_raw)
    df_all_costs = fetch_all_pupil_costs()
    st.markdown(f'<div class="banner-box"><h1 style="margin:0; color:white; font-size:28px;">🏛️ New Jersey School Finance Intelligence Platform</h1><p style="margin:5px 0 0 0; color:#cbd5e1; font-style:italic;">NJASBO 2026 Conference Executive Demo Engine</p></div>', unsafe_allow_html=True)
    geo_col1, geo_col2, geo_col3 = st.columns([2, 2, 4])
    with geo_col1: st.markdown(f'**Jurisdiction:** `{meta["county_name"]}` County')
    with geo_col2: st.markdown(f'**Legislative Cohort:** `District {leg_dist}`')
    with geo_col3: st.markdown(f'**System CDS Identification Code:** `{cds_padded}`')
    st.write('---')
    students = sum(int(row.get('student_count', 0)) for row in enroll_data) if enroll_data else 0
    spending_per_pupil = 0
    capital_outlay_spending = 0
    if costs_data:
        for row in costs_data:
            desc = str(row.get('line_desc', '')).lower()
            if 'classroom' in desc or 'instruction' in desc: spending_per_pupil = int(float(row.get('amount', 0)))
            if 'capital' in desc or 'outlay' in desc: capital_outlay_spending = int(float(row.get('amount', 0)))
    tab_ledger, tab_sfra, tab_peers, tab_macro = st.tabs(['📂 District Financial Ledger', '⚖️ SFRA Funding Adequacy Analyzer', '👥 Legislative Cohort Benchmarking', '🎯 Macro Funding Cohort Explorer'])
    with tab_ledger:
        st.subheader(f'📋 Core Fiscal Matrix: {selected_district}')
        fin_col1, fin_col2, fin_col3 = st.columns(3)
        with fin_col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric('Total Enrollment (On-Roll)', f'{students:,}' if students else 'Pre-Audit Baseline')
            st.markdown('</div>', unsafe_allow_html=True)
        with fin_col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric('Per-Pupil Budget Spending', f"${spending_per_pupil:,}" if spending_per_pupil else 'Pre-Audit Baseline')
            st.markdown('</div>', unsafe_allow_html=True)
        with fin_col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            try:
                fy26_surplus = [float(r.get('amount', 0)) for r in recap_data if 'surplus' in str(r.get('balance_type', '')).lower() and '26' in str(r.get('year', ''))]
                surplus_val = fy26_surplus[0] if fy26_surplus else max([float(r.get('amount', 0)) for r in recap_data if 'surplus' in str(r.get('balance_type', '')).lower()])
                surplus_display = f"${int(surplus_val):,}"
            except: surplus_display = 'Pre-Audit Baseline'
            st.metric('General Fund Surplus (FY26 Target)', surplus_display)
            st.markdown('</div>', unsafe_allow_html=True)
        if recap_data:
            st.write('')
            st.markdown('### 📈 10-Year General Fund Surplus Trend Horizon')
            try:
                trend_records = []
                for r in recap_data:
                    if 'surplus' in str(r.get('balance_type', '')).lower(): trend_records.append({'Fiscal Year': str(r.get('year', 'N/A')).strip(), 'Surplus Reserve Balance ($)': float(r.get('amount', 0))})
                df_trend = pd.DataFrame(trend_records).sort_values(by='Fiscal Year')
                if not df_trend.empty: st.area_chart(df_trend.set_index('Fiscal Year'), use_container_width=True)
            except: pass
    with tab_sfra:
        st.subheader('⚖️ Verified School Funding Reform Act (SFRA) Financial Adequacy Ledger')
        col_sfra1, col_sfra2 = st.columns(2)
        with col_sfra1:
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown('#### 🏛️ Real State Aid Adequacy Balance (Actual vs Uncapped)')
            if state_aid_data and len(state_aid_data) > 0:
                row = state_aid_data[0]
                actual_aid = float(row.get('Actual K-12 Aid') or 0)
                uncapped_aid = float(row.get('Uncapped Aid') or 0)
                adequacy_budget = float(row.get('Adequacy Budget') or 0)
                variance = float(row.get('Actual Minus Uncapped') or (actual_aid - uncapped_aid))
                m1, m2 = st.columns(2)
                m1.metric('Uncapped Formula Aid Target', f"${int(uncapped_aid):,}")
                m2.metric('Actual Capped Aid Allocation', f"${int(actual_aid):,}")
                st.write(f'**SFRA Adequacy Budget Base Limit:** `${int(adequacy_budget):,}`')
                if variance < 0: st.error(f'⚠️ **Formula Underfunding Deficit Gap:** This district is operating under an absolute funding deficit of `${int(abs(variance)):,}` relative to state formula targets.')
                else: st.success(f'✅ **Formula Alignment Target Met:** Capped allocations match or exceed basic parameters by `${int(variance):,}`.')
            else: st.warning('No row index matches found in the [State Aid Summary] layout table for this entity.')
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown('#### 📉 Local Tax Levy vs Local Property Wealth Thresholds')
            local_levy_total = 0
            if revenue_data:
                for r in revenue_data:
                    desc = str(r.get('line_desc', '')).lower()
                    if 'tax' in desc or 'levy' in desc or 'local school district tax' in desc: local_levy_total += float(r.get('amount') or 0)
            if local_levy_total:
                st.metric('Total Local Tax Levy Contribution Raised', f"\& ${int(local_levy_total):,}")
                if state_aid_data and len(state_aid_data) > 0:
                    lfs_val = float(state_aid_data[0].get('EQA_LSHR') or 0)
                    if lfs_val: st.metric('Formulated Local Fair Share Metric Target', f"${int(lfs_val):,}")
            else: st.warning('No localized tax line item declarations matching ledger indexes found for this entry row selection.')
            st.markdown('</div>', unsafe_allow_html=True)
        with col_sfra2:
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown('#### 🏢 Real Capital Reserve Accumulation Curve')
            cap_records = []
            if recap_data:
                for r in recap_data:
                    b_type = str(r.get('balance_type', '')).lower()
                    if 'capital' in b_type and 'reserve' in b_type: cap_records.append({'Fiscal Year': str(r.get('year', 'N/A')).strip(), 'Capital Reserve Balance ($)': float(r.get('amount', 0))})
            if cap_records:
                df_cap = pd.DataFrame(cap_records).sort_values(by='Fiscal Year')
                st.line_chart(df_cap.set_index('Fiscal Year'), use_container_width=True)
            else: st.warning('No multi-year Capital Reserve row tracking categories matching indices found for this item.')
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown('#### 🏗️ Real Capital Projects Expenditure Spending Flow')
            if capital_outlay_spending: st.metric('Verified Capital Outlay Expenditure (Fund 12/30)', f"${capital_outlay_spending:,}")
            else: st.warning('No explicit Capital Outlay layout assignments identified inside active records.')
            st.markdown('</div>', unsafe_allow_html=True)
    with tab_peers:
        st.subheader(f'👥 Regional Legislative Peer Benchmarking (District {leg_dist})')
        peers_df = df_maps[df_maps['legislative_district'] == leg_dist][['cds', 'county_name', 'district_name']].drop_duplicates(subset=['district_name'])
        if not df_all_costs.empty:
            df_all_costs['clean_cds'] = df_all_costs['cds'].astype(str).str.strip().str.zfill(6)
            vis_records = []
            for _, row in peers_df.iterrows():
                p_name = row['district_name']; p_cds = str(row['cds']).strip().zfill(6); p_raw = str(int(p_cds)); p_padded_local = p_cds.zfill(9)[:6] if len(p_cds) >= 8 else p_cds.zfill(6)
                match = df_all_costs[df_all_costs['clean_cds'].isin([p_padded_local, p_raw.zfill(6), p_cds])]
                if not match.empty:
                    val = match.iloc[0]['amount']
                    if pd.notna(val) and float(val) > 0: vis_records.append({'District': p_name, 'Per-Pupil Budget Spending ($)': int(float(val))})
            if vis_records:
                df_vis = pd.DataFrame(vis_records).sort_values(by='Per-Pupil Budget Spending ($)', ascending=False)
                st.bar_chart(df_vis.set_index('District'), use_container_width=True)
        peers_df.columns = ['Master CDS Code', 'County Jurisdiction Line', 'Associated School District']
        st.dataframe(peers_df.reset_index(drop=True), width='stretch')
    with tab_macro:
        st.subheader('🎯 Statewide Operational Cohort Explorer')
        macro_filter = st.selectbox('Select Macro Financial Target Filter:', ['Chronically Underfunded (Actual is Below Uncapped Formula Aid)', 'Overfunded / Formula-Stabilized Position'])
        if not df_global_aid.empty:
            var_col = 'Actual Minus Uncapped'; dist_col = 'distname'; cds_col = 'CDS_Code'; actual_col = 'Actual K-12 Aid'; uncapped_col = 'Uncapped Aid'; lfs_col = 'EQA_LSHR'
            if var_col in df_global_aid.columns:
                df_global_aid[var_col] = pd.to_numeric(df_global_aid[var_col], errors='coerce').fillna(0)
                if 'Chronically Underfunded' in macro_filter: res_df = df_global_aid[df_global_aid[var_col] < 0].sort_values(by=var_col)
                else: res_df = df_global_aid[df_global_aid[var_col] >= 0].sort_values(by=var_col, ascending=False)
                avail_cols = [c for c in [cds_col, dist_col, actual_col, uncapped_col, lfs_col, var_col] if c in df_global_aid.columns]
                st.dataframe(res_df[avail_cols].reset_index(drop=True), width='stretch')
            else: st.warning('Schema mismatch in State Aid Summary columns.')
        else: st.info('No records available in global adequacy ledger.')
