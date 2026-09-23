import urllib.request, urllib.error, json, sys, random
B = "http://localhost:8000"
R = []
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
s, d = q("GET", "/health"); R.append(("QA-01", "Health", s == 200 and d.get("status") == "ok"))
rs = random.randint(10000, 99999); s, d = q("POST", "/api/auth/register", {"nickname": "u1", "email": f"a{rs}@b.com", "password": "P123!"}); R.append(("QA-02", "Register", s == 200 and "token" in d))
rs = random.randint(10000, 99999); em = f"f{rs}@g.com"; s, d = q("POST", "/api/auth/register", {"nickname": f"U{rs}", "email": em, "password": "Test123!"})
if s == 200:
    T = d["token"]
    q("POST", "/api/auth/logout", headers={"Authorization": f"Token {T}"})
    s, d = q("POST", "/api/auth/login", {"email": em, "password": "Test123!"})
    if s == 200: T = d["token"]
    R.append(("QA-03", "AuthFlow", s == 200 and "token" in d))
else: R.append(("QA-03", "AuthFlow", False))
if T:
    s, d = q("POST", "/api/posts", {"content": "RedTeam test"}, {"Authorization": f"Token {T}"})
    R.append(("QA-04", "CreatePost", s == 200 and "post" in d))
else: R.append(("QA-04", "CreatePost", False))
if T:
    s, d = q("POST", "/api/posts", {"content": "X" * 501}, {"Authorization": f"Token {T}"})
    R.append(("QA-05", "Post>500", s in [422, 400] or (s == 200 and len(d.get("post",{}).get("content","")) <= 500)))
else: R.append(("QA-05", "Post>500", False))
s, d = q("POST", "/api/auth/register", {"nickname": "x"}); R.append(("QA-06", "MissFields", s in [422, 400]))
s, d = q("POST", "/api/auth/login", {"email": "x@y.com", "password": "wrong"}); R.append(("QA-07", "WrongPass", s in [401, 403, 400]))
if T:
    s, d = q("DELETE", "/api/posts/99999", headers={"Authorization": f"Token {T}"})
    R.append(("QA-08", "DelNonexist", s in [404, 403, 400]))
else: R.append(("QA-08", "DelNonexist", False))
if T:
    s, d = q("POST", "/api/users/1/follow", headers={"Authorization": f"Token {T}"})
    R.append(("QA-09", "FollowUser", s == 200))
else: R.append(("QA-09", "FollowUser", False))
s, d = q("POST", "/api/posts", {"content": "noauth"}); R.append(("QA-10", "NoAuthPost", s in [401, 403]))
pc = sum(1 for r in R if r[2]); fc = sum(1 for r in R if not r[2])
print("=" * 60)
print(f"{'Case':8} {'Feature':18} {'Status':8}")
print("=" * 60)
for r in R: print(f"{r[0]:8} {r[1]:18} {'PASS' if r[2] else 'FAIL':8}")
print("=" * 60)
print(f"Total: {len(R)}  Pass: {pc}  Fail: {fc}")
sys.exit(0 if fc == 0 else 1)
