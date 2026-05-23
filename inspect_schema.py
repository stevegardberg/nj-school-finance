import requests

DB_URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
HEADERS = {
    "apikey": "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Authorization": "Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Accept": "application/openapi+json"
}

r = requests.get(DB_URL, headers=HEADERS)

if r.status_code == 200:
    schema = r.json()
    definitions = schema.get("definitions", {})
    
    target_tables = ["UFB Revenue", "State Aid Summary", "UFB Appropriations", "revenue", "school_appropriations"]
    
    print("✨ --- Supabase Internal Schema Definition Map --- ✨")
    for table in target_tables:
        print(f"\n📋 Table: [{table}]")
        if table in definitions:
            properties = definitions[table].get("properties", {})
            columns = list(properties.keys())
            print(f"  🔹 Columns Found: {columns}")
        else:
            # Check case sensitivity variations or underscores
            alt_name = table.replace(" ", "_")
            if alt_name in definitions:
                properties = definitions[alt_name].get("properties", {})
                columns = list(properties.keys())
                print(f"  🔹 Columns Found (Mapped to {alt_name}): {columns}")
            else:
                print("  ❌ Schema definition template missing from root manifest.")
else:
    print(f"❌ Failed to retrieve API schema manifest. Status: {r.status_code}")
