import requests

URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/enrollment?cds=eq.140450"
HEADERS = {
    "apikey": "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Authorization": "Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y"
}

r = requests.get(URL, headers=HEADERS)
data = r.json()
print(f"Total rows found for Boonton Town: {len(data)}")
if data:
    print("Sample Row Data:", data[0])
