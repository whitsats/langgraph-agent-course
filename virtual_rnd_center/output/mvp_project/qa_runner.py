import urllib.request, urllib.error, json, sys, random

BASE = "http://localhost:8000"
results = []
token = None
user_id = None
email = None

def req(method, path, body=None, headers=None):
    if headers is None: headers = {}
    if body is not None: headers["Content-Type"] = "application/json"
    data = json.dumps(body).encode() if body else None
    o = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(o, timeout=10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return -1, str(e)

def record(cid, feat, ok):
    results.append((cid, feat, ok))

# QA-01 Health
s, d = req("GET", "/health")
record("QA-01", "Backend Health", s == 200 and d.get("status") == "ok")

# QA-02 Register
rs = random.randint(10000, 99999)
s, d = req("POST", "/api/auth/register", {"nickname": "u1", "email": f"a{rs}@b.com", "password": "P@ssw0rd!"})
record("QA-02", "Register User", s == 200 and "token" in d)

# QA-03 Full auth flow
rs = random.randint(10000, 99999)
email = f"f{rs}@g.com"
s, d = req("POST", "/api/auth/register", {"nickname": f"U{rs}", "email": email, "password": "Test123!"})
if s == 200:
    token = d["token"]
    user_id = d["user"]["id"]
    req("POST", "/api/auth/logout", headers={"Authorization": f"Token {token}"})
    s, d = req("POST", "/api/auth/login", {"email": email, "password": "Test123!"})
    if s == 200:
        token = d["token"]
    record("QA-03", "Auth Flow", s == 200 and "token" in d)
else:
    record("QA-03", "Auth Flow", False)

# QA-04 Create post
if token:
    s, d = req("POST", "/api/posts", {"content": "Red Team test post"}, {"Authorization": f"Token {token}"})
    record("QA-04", "Create Post", s == 200 and "post" in d)
else:
    record("QA-04", "Create Post", False)

# QA-05 Edge: 501 char post
if token:
    s, d = req("POST", "/api/posts", {"content": "X" * 501}, {"Authorization": f"Token {token}"})
    record("QA-05", "Post >500 chars", s in [422, 400] or (s == 200 and len(d.get("post",{}).get("content","")) <= 500))
else:
    record("QA-05", "Post >500 chars", False)

# QA-06 Failure: Missing fields
s, d = req("POST", "/api/auth/register", {"nickname": "x"})
record("QA-06", "Missing Fields", s in [422, 400])

# QA-07 Failure: Wrong password
s, d = req("POST", "/api/auth/login", {"email": "x@y.com", "password": "wrong"})
record("QA-07", "Wrong Password", s in [401, 403, 400])

# QA-08 Edge: Delete nonexistent
if token:
    s, d = req("DELETE", "/api/posts/99999", headers={"Authorization": f"Token {token}"})
    record("QA-08", "Del Nonexistent", s in [404, 403, 400])
else:
    record("QA-08", "Del Nonexistent", False)

# QA-09 Functional: Follow
if token:
    s, d = req("POST", "/api/users/1/follow", headers={"Authorization": f"Token {token}"})
    record("QA-09", "Follow User", s == 200)
else:
    record("QA-09", "Follow User", False)

# QA-10 Edge: No auth
s, d = req("POST", "/api/posts", {"content": "noauth"})
record("QA-10", "No Auth Post", s in [401, 403])

# Print results
pc = sum(1 for r in results if r[2])
fc = sum(1 for r in results if not r[2])
print("=" * 60)
print(f"{'Case':8} {'Feature':20} {'Status':8}")
print("=" * 60)
for r in results:
    print(f"{r[0]:8} {r[1]:20} {'PASS' if r[2] else 'FAIL':8}")
print("=" * 60)
print(f"Total: {len(results)}, Pass: {pc}, Fail: {fc}")
sys.exit(0 if fc == 0 else 1)
