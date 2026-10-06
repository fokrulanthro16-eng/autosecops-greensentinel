import json
import time
import urllib.error
import urllib.request

API_KEY = "rnd_bfevtkdSKg8ToYlClIvzJEqMxZ1W"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "AutoSecOps-Deployer"
}

def make_request(url, method="GET", data=None):
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {err_body}")
        raise

print("Fetching Render owner account...")
owners_resp = make_request("https://api.render.com/v1/owners")
owner_id = owners_resp[0]["owner"]["id"]
print(f"Owner verified: {owner_id}")

print("Checking existing services...")
services = make_request("https://api.render.com/v1/services?limit=20")
service_url = None
service_id = None

for item in services:
    svc = item.get("service", {})
    if svc.get("name") == "autosecops-greensentinel":
        service_id = svc.get("id")
        service_url = svc.get("serviceDetails", {}).get("url")
        print(f"Service already exists (ID: {service_id})")
        break

if not service_id:
    print("Creating new Web Service on Render...")
    payload = {
        "type": "web_service",
        "name": "autosecops-greensentinel",
        "ownerId": owner_id,
        "repo": "https://github.com/fokrulanthro16-eng/autosecops-greensentinel",
        "autoDeploy": "yes",
        "branch": "main",
        "serviceDetails": {
            "env": "docker",
            "plan": "free",
            "region": "frankfurt"
        }
    }
    created = make_request("https://api.render.com/v1/services", method="POST", data=payload)
    service_id = created["service"]["id"]
    service_url = created["service"].get("serviceDetails", {}).get("url")
    print(f"Service successfully created! (ID: {service_id})")

print("Triggering fresh deploy...")
deploy_resp = make_request(f"https://api.render.com/v1/services/{service_id}/deploys", method="POST", data={"clearCache": "do_not_clear"})
deploy_id = deploy_resp.get("id")
print(f"Deploy triggered successfully! (Deploy ID: {deploy_id})")

print("\n" + "="*50)
print(f"[LIVE URL] {service_url}")
print("="*50)
