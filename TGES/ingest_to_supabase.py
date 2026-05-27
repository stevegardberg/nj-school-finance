import pandas as pd
import numpy as np
import os
from supabase import create_client

SUPABASE_URL = "https://exqwkzidanuywriatmhi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4cXdremlkYW51eXdyaWF0bWhpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxNTQ3NzYsImV4cCI6MjA5MjczMDc3Nn0.y_-nctPy90m8Mj0WWqCZiXaT0_bNkTeVDegxn1_PzsE"
FOLDER_PATH = '/Users/steve/nj-school-finance/TGES'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_ingestion():
    for root, dirs, files in os.walk(FOLDER_PATH):
        for filename in files:
            if filename.lower().endswith(('.csv', '.xlsx')):
                file_path = os.path.join(root, filename)
                try:
                    if filename.lower().endswith('.csv'):
                        df = pd.read_csv(file_path, encoding='latin1')
                    else:
                        df = pd.read_excel(file_path, header=2)
                    
                    # Force all numeric values to be finite (no Infinity or NaN)
                    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
                    
                    dist_col = next((c for c in df.columns if 'dist' in str(c).lower()), None)
                    if dist_col:
                        df['cds_code'] = df[dist_col].astype(str).str.split('.').str[0].str.zfill(6)
                        df['fiscal_year'] = filename.split('_')[-1].split('.')[0]
                        df['filename'] = filename
                        
                        df_melted = df.melt(id_vars=['cds_code', 'fiscal_year', 'filename'], 
                                            var_name='metric_name', value_name='metric_value')
                        
                        # Convert metric_value to string to be safe
                        df_melted['metric_value'] = df_melted['metric_value'].astype(str)
                        
                        records = df_melted.to_dict(orient='records')
                        supabase.table('tges_metrics').insert(records).execute()
                        print(f"✅ Successfully uploaded: {filename}")
                    else:
                        print(f"⚠️ Skipped: No 'dist' column in {filename}")
                except Exception as e:
                    print(f"❌ Error in {filename}: {e}")

run_ingestion()