import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")

# 1. SETUP & CONFIGURATION (Direct Fallback to Prevent Key Mismatches)
supabase_config = st.secrets.get("supabase", {})
SUPABASE_URL = supabase_config.get(
    "url", "https://exqwkzidanuywriatmhi.supabase.co"
)
SUPABASE_KEY = supabase_config.get(
    "key",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4cXdremlkYW51eXdyaWF0bWhpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxNTQ3NzYsImV4cCI6MjA5MjczMDc3Nn0.y_-nctPy90m8Mj0WWqCZiXaT0_bNkTeVDegxn1_PzsE",
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# 2. DATA ARCHITECTURE: INGESTION & CLEANING PROTOCOL
@st.cache_data(ttl=3600)
def fetch_table(table):
  all_records = []
  batch_size = 1000
  start = 0
  while True:
    try:
      res = (
          supabase.table(table)
          .select("*")
          .range(start, start + batch_size - 1)
          .execute()
      )
      data = res.data
      if not data:
        break
      all_records.extend(data)
      if len(data) < batch_size:
        break
      start += batch_size
    except Exception as e:
      st.error(f"Supabase Error on table `{table}`: {e}")
      break
  return pd.DataFrame(all_records)


@st.cache_data(ttl=3600)
def get_data():
  df_sum = fetch_table("state_aid_summary")
  df_map = fetch_table("legislative_mapping")
  df_types = fetch_table("vw_district_cohorts")

  for df in [df_sum, df_map, df_types]:
    if not df.empty:
      df.columns = df.columns.astype(str).str.lower().str.strip()
      rename_map = {
          "coname": "county_name",
          "county name": "county_name",
          "distname": "district_name",
          "district name": "district_name",
          "cds code": "cds",
          "cds_code": "cds",
          "district type": "district_type",
      }
      df = df.rename(columns=rename_map)
    else:
      df.columns = pd.Index([])

  for df in [df_sum, df_map, df_types]:
    if "cds" in df.columns:
      df["cds"] = (
          df["cds"]
          .astype(str)
          .str.replace(r"\.0$", "", regex=True)
          .str.zfill(6)
      )
    if "county_name" in df.columns:
      df["county_name"] = (
          df["county_name"].astype(str).str.title().str.strip()
      )
    if "district_name" in df.columns:
      df["district_name"] = (
          df["district_name"].astype(str).str.title().str.strip()
      )

  df_merged = df_sum.copy()
  if "cds" in df_merged.columns and "cds" in df_map.columns:
    df_merged = df_merged.merge(df_map[["cds", "ld_display"]], on="cds", how="left")
  if "cds" in df_merged.columns and "cds" in df_types.columns:
    type_cols = [c for c in ["cds", "district_type"] if c in df_types.columns]
    df_merged = df_merged.merge(df_types[type_cols], on="cds", how="left")

  if "county_name" not in df_merged.columns:
    df_merged["county_name"] = "Unassigned"
  if "district_type" not in df_merged.columns:
    df_merged["district_type"] = "Unknown"
  else:
    df_merged["district_type"] = df_merged["district_type"].fillna("Unknown")

  if "ld_display" not in df_merged.columns:
    df_merged["ld_display"] = "Unknown"

  return df_merged


def add_metrics(df):
  if df.empty:
    return df
  if "district_name" not in df.columns:
    df["district_name"] = "Unknown"

  if "cds" in df.columns:
    df["district_name"] = df["district_name"].fillna("Unknown").astype(str)
    df["cds"] = df["cds"].fillna("").astype(str)
    dist_code = df["cds"].str.zfill(6).str[-4:]
    df["district_name"] = df["district_name"].str.split(" \(").str[0]
    df["district_name"] = df["district_name"] + " (" + dist_code + ")"

  sort_cols = [c for c in ["district_name", "fiscal_year"] if c in df.columns]
  if sort_cols:
    df = df.sort_values(sort_cols)

  num_cols = [
      "actual_state_aid",
      "uncapped_aid",
      "adequacy_budget",
      "actual_tax_levy",
      "equalized_valuation",
      "local_fair_share",
      "district_income",
  ]
  for col in num_cols:
    if col in df.columns:
      if df[col].dtype == object:
        cleaned = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
        )
        cleaned = cleaned.str.replace(r"\((.*?)\)", r"-\1", regex=True)
        df[col] = pd.to_numeric(cleaned, errors="coerce").fillna(0)
      else:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

  if "district_name" in df.columns and "fiscal_year" in df.columns:
    if "actual_state_aid" in df.columns:
      df["Pct_Change_Aid"] = (
          df.groupby("district_name")["actual_state_aid"]
          .pct_change()
          .fillna(0)
      )
    if "actual_tax_levy" in df.columns:
      df["Pct_Change_Levy"] = (
          df.groupby("district_name")["actual_tax_levy"]
          .pct_change()
          .fillna(0)
      )

  if "actual_state_aid" in df.columns and "uncapped_aid" in df.columns:
    df["Over_Under_Funded"] = df["actual_state_aid"] - df["uncapped_aid"]
  if "actual_tax_levy" in df.columns and "local_fair_share" in df.columns:
    df["Over_Under_LFS"] = df["actual_tax_levy"] - df["local_fair_share"]
  if "actual_tax_levy" in df.columns and "equalized_valuation" in df.columns:
    df["Tax_Levy_per_100"] = (
        df["actual_tax_levy"] / df["equalized_valuation"].replace(0, 1)
    ) * 100
  if "actual_tax_levy" in df.columns and "district_income" in df.columns:
    df["Tax_Levy_per_100_Income"] = (
        df["actual_tax_levy"] / df["district_income"].replace(0, 1)
    ) * 100
  return df


def get_formatted_matrix(df, is_multi_row=False):
  if df.empty:
    return df

  if "fiscal_year" in df.columns:
    col_order = [
        "fiscal_year",
        "adequacy_budget",
        "uncapped_aid",
        "actual_state_aid",
        "Over_Under_Funded",
        "Pct_Change_Aid",
        "local_fair_share",
        "actual_tax_levy",
        "Over_Under_LFS",
        "Pct_Change_Levy",
        "equalized_valuation",
        "Tax_Levy_per_100",
        "district_income",
        "Tax_Levy_per_100_Income",
    ]
  else:
    col_order = [
        "district_name",
        "county_name",
        "district_type",
        "adequacy_budget",
        "uncapped_aid",
        "actual_state_aid",
        "Over_Under_Funded",
        "local_fair_share",
        "actual_tax_levy",
        "Over_Under_LFS",
        "equalized_valuation",
        "Tax_Levy_per_100",
        "district_income",
        "Tax_Levy_per_100_Income",
    ]

  df_out = df[[c for c in col_order if c in df.columns]].copy()

  rename = {
      "fiscal_year": "Fiscal Year",
      "district_name": "District Name",
      "county_name": "County",
      "district_type": "District Type",
      "adequacy_budget": "Adequacy Budget",
      "uncapped_aid": "Uncapped Aid",
      "actual_state_aid": "Actual Aid",
      "Over_Under_Funded": "Over/Under Funded",
      "Pct_Change_Aid": "% Change Actual Aid",
      "local_fair_share": "Local Fair Share",
      "actual_tax_levy": "Actual Levy",
      "Over_Under_LFS": "Over/Under LFS",
      "Pct_Change_Levy": "% Change Actual Levy",
      "equalized_valuation": "Equalized Valuation",
      "Tax_Levy_per_100": "Levy per $100",
      "district_income": "District Income",
      "Tax_Levy_per_100_Income": "Levy per $100 Income",
  }
  df_out = df_out.rename(columns=rename)

  if is_multi_row:
    return df_out

  for col in df_out.columns:
    if col not in ["Fiscal Year", "District Name", "County", "District Type"]:
      df_out[col] = df_out[col].apply(
          lambda x: (
              f"${float(x):,.0f}"
              if "%" not in col and "per $100" not in col.lower()
              else (
                  f"{float(x):.2%}"
                  if "%" in col
                  else (
                      f"{float(x):.4f}"
                      if "per $100" in col.lower()
                      else f"${float(x):,.0f}"
                  )
              )
          )
      )
  return df_out


# Load data
df_merged = add_metrics(get_data())

# Top Navigation Bar
st.markdown("### 🏛️ New Jersey School Finance Intelligence Platform")
app_mode = st.selectbox(
    "Navigation View",
    [
        "District Financial Ledger",
        "District Type Trends",
        "Legislative District Trends",
        "District Comparison Leaderboard",
    ],
)
st.markdown("---")

if not df_merged.empty:
  if app_mode == "District Financial Ledger":
    c1, c2, c3, c4 = st.columns(4)
    sel_ld = (
        c1.selectbox(
            "1️⃣ Legislative:",
            ["All"]
            + sorted(df_merged["ld_display"].dropna().unique().tolist()),
        )
        if "ld_display" in df_merged.columns
        else "All"
    )
    sel_type = (
        c2.selectbox(
            "2️⃣ District Type:",
            ["All"]
            + sorted(df_merged["district_type"].dropna().unique().tolist()),
        )
        if "district_type" in df_merged.columns
        else "All"
    )
    sel_county = (
        c3.selectbox(
            "3️⃣ County:",
            ["All"]
            + sorted(df_merged["county_name"].dropna().unique().tolist()),
        )
        if "county_name" in df_merged.columns
        else "All"
    )

    df_f = df_merged.copy()
    if sel_ld != "All" and "ld_display" in df_f.columns:
      df_f = df_f[df_f["ld_display"] == sel_ld]
    if sel_type != "All" and "district_type" in df_f.columns:
      df_f = df_f[df_f["district_type"] == sel_type]
    if sel_county != "All" and "county_name" in df_f.columns:
      df_f = df_f[df_f["county_name"] == sel_county]

    districts = (
        sorted(df_f["district_name"].dropna().unique().tolist())
        if "district_name" in df_f.columns
        else []
    )
    sel_district = c4.selectbox("4️⃣ District:", ["Select..."] + districts)

    if sel_district != "Select...":
      target = df_f[df_f["district_name"] == sel_district]
      st.subheader(f"📍 Financial Ledger: {sel_district}")
      st.dataframe(
          get_formatted_matrix(target),
          use_container_width=True,
          hide_index=True,
          height=420,
      )
      for name, group_col, val in [
          (
              "Legislative District",
              "ld_display",
              (
                  target["ld_display"].iloc[0]
                  if "ld_display" in target.columns and not target.empty
                  else None
              ),
          ),
          (
              "District Type",
              "district_type",
              (
                  target["district_type"].iloc[0]
                  if "district_type" in target.columns and not target.empty
                  else None
              ),
          ),
      ]:
        if val and val != "Unknown":
          st.markdown("---")
          st.subheader(f"🏛️ {name} Average: {val}")
          peers = (
              df_merged[df_merged[group_col] == val].copy()
              if group_col in df_merged.columns
              else pd.DataFrame()
          )
          if not peers.empty and "fiscal_year" in peers.columns:
            avg = peers.groupby("fiscal_year").mean(numeric_only=True).reset_index()
            st.dataframe(
                get_formatted_matrix(add_metrics(avg)),
                use_container_width=True,
                hide_index=True,
                height=420,
            )

  elif app_mode == "District Type Trends":
    st.markdown("### 📊 Multi-Year Averages Across All District Types")
    st.markdown(
        "*Scroll down to compare multi-year financial trends stacked by district"
        " type.*"
    )
    if "district_type" in df_merged.columns:
      type_grouped = (
          df_merged.groupby(["district_type", "fiscal_year"])
          .mean(numeric_only=True)
          .reset_index()
      )
      for dt in sorted(type_grouped["district_type"].dropna().unique().tolist()):
        st.markdown(f"---")
        st.subheader(f"District Type: {dt}")
        filtered_type = type_grouped[type_grouped["district_type"] == dt].copy()
        st.dataframe(
            get_formatted_matrix(filtered_type),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

  elif app_mode == "Legislative District Trends":
    st.markdown("### 🏛 Multi-Year Averages Across All Legislative Districts")
    st.markdown(
        "*Scroll down to compare multi-year financial trends stacked by"
        " legislative district.*"
    )
    if "ld_display" in df_merged.columns:
      ld_grouped = (
          df_merged.groupby(["ld_display", "fiscal_year"])
          .mean(numeric_only=True)
          .reset_index()
      )
      for ld in sorted(ld_grouped["ld_display"].dropna().unique().tolist()):
        st.markdown(f"---")
        st.subheader(f"Legislative District: {ld}")
        filtered_ld = ld_grouped[ld_grouped["ld_display"] == ld].copy()
        st.dataframe(
            get_formatted_matrix(filtered_ld),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

  elif app_mode == "District Comparison Leaderboard":
    st.markdown("### 🏆 District Comparison Leaderboard (Multi-Year Sums)")
    st.markdown(
        "*One row per district summing all available fiscal years. Click any"
        " column header to sort numerically.*"
    )

    meta_cols = ["district_name", "county_name", "district_type"]
    available_meta = [c for c in meta_cols if c in df_merged.columns]

    sum_cols = [
        "adequacy_budget",
        "uncapped_aid",
        "actual_state_aid",
        "actual_tax_levy",
        "equalized_valuation",
        "local_fair_share",
        "district_income",
    ]
    available_sums = [c for c in sum_cols if c in df_merged.columns]

    if available_meta and available_sums:
      df_leaderboard = (
          df_merged.groupby(available_meta)[available_sums].sum().reset_index()
      )

      if (
          "actual_state_aid" in df_leaderboard.columns
          and "uncapped_aid" in df_leaderboard.columns
      ):
        df_leaderboard["Over_Under_Funded"] = (
            df_leaderboard["actual_state_aid"] - df_leaderboard["uncapped_aid"]
        )
      if (
          "actual_tax_levy" in df_leaderboard.columns
          and "local_fair_share" in df_leaderboard.columns
      ):
        df_leaderboard["Over_Under_LFS"] = (
            df_leaderboard["actual_tax_levy"] - df_leaderboard["local_fair_share"]
        )
      if (
          "actual_tax_levy" in df_leaderboard.columns
          and "equalized_valuation" in df_leaderboard.columns
      ):
        df_leaderboard["Tax_Levy_per_100"] = (
            df_leaderboard["actual_tax_levy"]
            / df_leaderboard["equalized_valuation"].replace(0, 1)
        ) * 100
      if (
          "actual_tax_levy" in df_leaderboard.columns
          and "district_income" in df_leaderboard.columns
      ):
        df_leaderboard["Tax_Levy_per_100_Income"] = (
            df_leaderboard["actual_tax_levy"]
            / df_leaderboard["district_income"].replace(0, 1)
        ) * 100

      formatted_ld = get_formatted_matrix(df_leaderboard, is_multi_row=True)

      currency_cols = [
          c
          for c in formatted_ld.columns
          if c
          not in [
              "District Name",
              "County",
              "District Type",
              "Levy per $100",
              "Levy per $100 Income",
          ]
      ]
      column_config = {
          col: st.column_config.NumberColumn(format="dollar")
          for col in currency_cols
      }
      if "Levy per $100" in formatted_ld.columns:
        column_config["Levy per $100"] = st.column_config.NumberColumn(
            format="$%,.4f"
        )
      if "Levy per $100 Income" in formatted_ld.columns:
        column_config["Levy per $100 Income"] = (
            st.column_config.NumberColumn(format="$%,.4f")
        )

      st.dataframe(
          formatted_ld,
          use_container_width=True,
          hide_index=True,
          column_config=column_config,
          height=750,
      )
else:
  st.warning(
      "No data retrieved from Supabase. Verify table permissions and Row Level"
      " Security (RLS) policies in your Supabase project settings."
  )
