import urllib.request
import json

print("\n" + "=" * 75)
print(f" {'PORT':<8} {'SERVICE NAME':<26} {'STATUS':<10} {'MODE':<25}")
print("=" * 75)

found = 0
for port in range(8000, 8015):
    try:
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "PortChecker"})
        with urllib.request.urlopen(req, timeout=0.8) as r:
            data = json.loads(r.read().decode())
            svc = data.get("service", "DocuGen Studio")
            mode = data.get("mode", "Admin Studio UI")
            stat = data.get("status", "ONLINE")
            print(f" {port:<8} {svc:<26} {stat:<10} {mode:<25}")
            found += 1
    except Exception:
        pass

if found == 0:
    print(" No active microservices detected on ports 8000-8015.")

print("=" * 75 + "\n")
