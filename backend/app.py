import streamlit as st
import pandas as pd
import numpy as np

# ... (Include your existing database handshake and fetch functions here) ...

# -----------------------------------------------------------------------------
# FINANCIAL METRICS ENGINE
# -----------------------------------------------------------------------------
def calculate_advanced_metrics(df_group):
    """
    Computes YoY % changes and tax levy rates safely.
    Ensures calculations are performed on year-ordered data.
    """
    df = df_group.sort_values("fiscal_year").copy()
    
    # 1. State Aid % Change
    df["state_aid_pct_change"] = df["actual_net_payout"].pct_change().fillna(0.0) * 100.0
    
    # 2. Tax Levy % Change
    df["tax_levy_pct_change"] = df["actual_tax_levy"].pct_change().fillna(0.0) * 100.0
    
    # 3. Tax Rate per $100 Valuation
    # Formula: (Actual Tax Levy / Equalized Valuation) * 100
    df["tax_rate_per_100"] = np.where(
        df["equalized_valuation"] > 0, 
        (df["actual_tax_levy"] / df["equalized_valuation"]) * 100.0, 
        0.0
    )
    return df

# Apply this to your district-specific data:
# df_processed = calculate_advanced_metrics(df_district_history)