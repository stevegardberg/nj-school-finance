import requests

URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1"
HEADERS = {
    "apikey": "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Authorization": "Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y"
}

print("--- TESTING ENROLLMENT TABLE ---")
r1 = requests.get(f"{URL}/enrollment?select=*&limit=1", headers=HEADERS)
print("Status:", r1.status_code)
print("Data Sample:", r1.json())

print("\n--- TESTING PUPIL COSTS TABLE ---")
r2 = requests.get(f"{URL}/pupil_costs?select=*&limit=1", headers=HEADERS)
print("Status:", r2.status_code)
print("Data Sample:", r2.json())
