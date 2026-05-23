import requests
import urllib.parse

DB_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
HEADERS = {
    "apikey": "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Authorization": "Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y"
}

# Explicitly test all tables in your true database asset list
tables = ["UFB Revenue", "State Aid Summary", "UFB Appropriations", "revenue", "school_appropriations"]

for table in tables:
    # Safely percent-encode table names with spaces (e.g., 'UFB%20Revenue')
    encoded_table = urllib.parse.quote(table)
    r = requests.get(f"{DB_URL}/{encoded_table}?limit=1", headers=HEADERS)
    
    print(f"\n--- Scanning Table: [{table}] ---")
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        if data and len(data) > 0:
            print("✅ Sample Keys Found:")
            print(list(data[0].keys()))
            print("Sample Content Row:", data[0])
        else:
            # Table is populated but this specific query layout came back empty
            print("⚠️ Table accessible but returned an empty array []. Attempting to inspect columns via OPTIONS request...")
            opt_r = requests.options(f"{DB_URL}/{encoded_table}", headers=HEADERS)
            if 'definitions' in opt_r.text or 'properties' in opt_r.text:
                print("Found columns in table properties definition template.")
            else:
                print(f"Raw body snapshot: {r.text[:200]}")
    else:
        print(f"❌ Table Unreachable. Message: {r.text[:200]}")
