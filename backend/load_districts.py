import pandas as pd
import requests

# Restructuring the pipeline to utilize standard web-safe network architecture
SUPABASE_URL = "https://exqwkzidanuywriatmhi.supabase.co"
# Your verified public Publishable tracking token
SUPABASE_KEY = "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y"

CSV_FILE_PATH = "raw_data/legislative_districts.csv"

def run_database_ingest():
    print("🚀 Initiating New Jersey Legislative Mapping Pipeline...")
    
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        print(f"📖 Loaded {len(df)} rows from raw data workspace.")
    except Exception as e:
        print(f"❌ Critical Failure: Unable to locate or parse CSV file. Details: {e}")
        return

    print("⚙️  Standardizing primary key string parameters...")
    df['co_pad'] = df['CO'].astype(str).str.zfill(2)
    df['dist_pad'] = df['DIST'].astype(str).str.zfill(4)
    df['cds_key'] = df['co_pad'] + df['dist_pad']
    df['county_clean'] = df['CONAME'].str.title()
    df['district_clean'] = df['DISTNAME'].str.title()

    print("🔌 Opening HTTP Web Gateway to Supabase Table Ledger...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # Tells Supabase to skip duplicate rows smoothly
    }

    # Transform your local DataFrame records into a structured web JSON payload bundle
    payload = []
    for _, row in df.iterrows():
        payload.append({
            "cds": row['cds_key'],
            "county_name": row['county_clean'],
            "district_name": row['district_clean'],
            "legislative_district": int(row['LEG_DIST'])
        })

    target_endpoint = f"{SUPABASE_URL}/rest/v1/legislative_mapping"
    
    try:
        # Pushing the dataset up over standard web browser protocols
        response = requests.post(target_endpoint, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            print("\n=======================================================")
            print(f"🎉 Pipeline Complete! {len(payload)} rows securely uploaded to Supabase!")
            print("=======================================================")
        else:
            print(f"❌ HTTP Web Gateway Error {response.status_code}: {response.text}")
            print("💡 Reminder: Make sure the 'Enable Data API' toggle is checked in your dashboard settings tab!")
            
    except Exception as e:
        print(f"❌ Network Web Request Interrupted. Details: {e}")

if __name__ == "__main__":
    run_database_ingest()