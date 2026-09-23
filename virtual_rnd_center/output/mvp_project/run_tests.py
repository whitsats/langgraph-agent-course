import urllib.request, urllib.error, json, sys, random

B = "http://localhost:8000"
T = None

def q(m, p, b=None, h=None):
    if h is None: h = {}
    if b is not None: h["Content-Type"] = "application/json"
    d = json.dumps(b).encode() if b else None
    o = urllib.request.Request(B + p, data=d, headers=h, method=m)
    try:
        r = urllib.request.urlopen(o, timeout=10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return -1, str(e)

results = []
names = ["Backend Health", "User Registration", "Auth Flow (Login)", "Create Post",
         "Post >500 chars", "Missing Fields", "Wrong Password",
         "Delete Non-Existent", "Follow User", "Unauthorized Post"]

s, d = q("GET", "/health"); results.append(("QA-01", s == 200 and d.get("status") == "ok"))
rs = random.randint(10000, 99999); s, d = q("POST", "/api/auth/register", {"nickname": "u1", "email": "a" + str(rs) + "@b.com", "password": "P123!"}); results.append(("QA-02", s == 200 and "token" in d))
rs = random.randint(10000, 99999); em = "f" + str(rs) + "@g.com"; s, d = q("POST", "/api/auth/register", {"nickname": "U" + str(rs), "email": em, "password": "Test123!"})
if s == 200:
    T = d["token"]
    q("POST", "/api/auth/logout", headers={"Authorization": "Token " + T})
    s, d = q("POST", "/api/auth/login", {"email": em, "password": "Test123!"})
    if s == 200: T = d["token"]
    results.append(("QA-03", s == 200 and "token" in d))
else: results.append(("QA-03", False))
if T:
    s, d = q("POST", "/api/posts", {"content": "RedTeam test"}, {"Authorization": "Token " + T}); results.append(("QA-04", s == 200 and "post" in d))
    s, d = q("POST", "/api/posts", {"content": "X" * 501}, {"Authorization": "Token " + T}); ok = s in [422, 400] or (s == 200 and len(d.get("post", {}).get("content", "")) <= 500); results.append(("QA-05", ok))
else: results.append(("QA-04", False)); results.append(("QA-05", False))
s, d = q("POST", "/api/auth/register", {"nickname": "x"}); results.append(("QA-06", s in [422, 400]))
s, d = q("POST", "/api/auth/login", {"email": "x@y.com", "password": "wrong"}); results.append(("QA-07", s in [401, 403, 400]))
if T:
    s, d = q("DELETE", "/api/posts/99999", headers={"Authorization": "Token " + T}); results.append(("QA-08", s in [404, 403, 400]))
    s, d = q("POST", "/api/users/1/follow", headers={"Authorization": "Token " + T}); results.append(("QA-09", s == 200))
else: results.append(("QA-08", False)); results.append(("QA-09", False))
s, d = q("POST", "/api/posts", {"content": "noauth"}); results.append(("QA-10", s in [401, 403]))

pc = sum(1 for r in results if r[1]); fc = sum(1 for r in results if not r[1])
print("=" * 70)
print("{:<10} {:<30} {:<10}".format("Case ID", "Feature", "Status"))
print("=" * 70)
for i, r in enumerate(results):
    print("{:<10} {:<30} {:<10}".format(r[0], names[i], "PASS" if r[1] else "FAIL"))
print("=" * 70)
print("Total: {} | Pass: {} | Fail: {}".format(len(results), pc, fc))
sys.exit(0 if fc == 0 else 1)
