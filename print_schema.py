import requests

URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
HEADERS = {
    "apikey": "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Authorization": "Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y"
}

# SQL payload to extract custom tables and their column metadata
sql_query = """
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'public' 
ORDER BY table_name, ordinal_position;
"""

# Fetch the tables list using an RPC configuration call
res = requests.get(f"{URL}/rpc/get_schema", headers=HEADERS)

if res.status_code == 404:
    print("💡 PostgREST RPC not enabled yet. Swapping to a direct table-check strategy instead...\n")
    target_tables = ['legislative_mapping', 'enrollment', 'pupil_costs']
    for table in target_tables:
        r = requests.get(f"{URL}/{table}?select=*&limit=1", headers=HEADERS)
        if r.status_code == 200 and r.json():
            print(f"📋 Table: public.{table}")
            print(f"   Columns found: {list(r.json()[0].keys())}\n")
        elif r.status_code == 200:
            print(f"📋 Table: public.{table} (Table is currently empty but accessible)")
        else:
            print(f"❌ Table: public.{table} could not be reached (Status {r.status_code})")
else:
    print(res.json())
