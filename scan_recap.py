import requests

URL = "https://exqwkzidanuywriatmhi.supabase.co/rest/v1/recap_balance?select=*&limit=1"
HEADERS = {
    "apikey": "sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y",
    "Authorization": "Bearer sb_publishable_Z5yYaxAksQTfk_v5ukdovg_jZqMSs6y"
}

r = requests.get(URL, headers=HEADERS)
if r.status_code == 200 and r.json():
    print("🎯 RECAP_BALANCE TABLE ACTIVE!")
    print("Columns found:", list(r.json()[0].keys()))
elif r.status_code == 200:
    print("📋 Table exists but appears empty. Let's verify RLS status.")
else:
    print(f"❌ Error reaching table. Status Code: {r.status_code}")
