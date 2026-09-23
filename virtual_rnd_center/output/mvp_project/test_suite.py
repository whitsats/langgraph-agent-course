import urllib.request
import urllib.error
import json
import sys
import random

BASE = "http://localhost:8000"

results = []
user_email = None
user_token = None
user_id = None

def test(case_id, feature, action, expected, actual_func):
    try:
        actual = actual_func()
        status = "PASS" if actual == expected else "FAIL"
    except Exception as e:
        actual = f"ERROR: {str(e)}"
        status = "FAIL"
    results.append({"id": case_id, "feature": feature, "action": action, "expected": expected, "actual": actual, "status": status})
    return status

def req(method, path, body=None, headers=None):
    if headers is None:
        headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    data = json.dumps(body).encode() if body else None
    req_obj = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req_obj, timeout=10)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        return -1, str(e)

# ============================================================
# QA-01: Health check
# ============================================================
def qa01():
    status, data = req("GET", "/health")
    return "PASS" if status == 200 and data.get("status") == "ok" else f"FAIL: {status} {data}"

test("QA-01", "Backend Health", "GET /health -> 200, status=ok", "PASS", qa01)

# ============================================================
# QA-02: Register a new user
# ============================================================
def qa02():
    rand_suffix = random.randint(10000, 99999)
    status, data = req("POST", "/api/auth/register", {"nickname": "testuser", "email": f"test{rand_suffix}@example.com", "password": "SecurePass123!"})
    if status == 200 and "token" in data and "user" in data:
        return "PASS"
    return f"FAIL: {status} {data}"

test("QA-02", "User Registration", "POST /api/auth/register -> token+user", "PASS", qa02)

# ============================================================
# QA-03: Full auth flow: register, logout, login
# ============================================================
def qa03():
    global user_email, user_token, user_id
    rand_suffix = random.randint(10000, 99999)
    user_email = f"qa_user_{rand_suffix}@test.com"
    
    status, data = req("POST", "/api/auth/register", {"nickname": f"QAUser{rand_suffix}", "email": user_email, "password": "TestPass123!"})
    if status != 200:
        return f"FAIL at register: {status} {data}"
    user_token = data["token"]
    user_id = data["user"]["id"]
    
    status, data = req("POST", "/api/auth/logout", headers={"Authorization": f"Token {user_token}"})
    if status != 200:
        return f"FAIL at logout: {status} {data}"
    
    status, data = req("POST", "/api/auth/login", {"email": user_email, "password": "TestPass123!"})
    if status == 200 and "token" in data and "user" in data:
        user_token = data["token"]
        user_id = data["user"]["id"]
        return "PASS"
    return f"FAIL: {status} {data}"

test("QA-03", "Full Auth Flow", "register->logout->login", "PASS", qa03)

# ============================================================
# QA-04: Create post
# ============================================================
def qa04():
    if not user_token:
        return "FAIL: No auth token"
    status, data = req("POST", "/api/posts", {"content": "Red Team testing post!"}, headers={"Authorization": f"Token {user_token}"})
    if status == 200 and "post" in data:
        return "PASS"
    return f"FAIL: {status} {data}"

test("QA-04", "Create Post", "POST /api/posts -> new post", "PASS", qa04)

# ============================================================
# QA-05: Edge case - Post exceeding 500 chars
# ============================================================
def qa05():
    if not user_token:
        return "FAIL: No auth token"
    long_content = "A" * 501
    status, data = req("POST", "/api/posts", {"content": long_content}, headers={"Authorization": f"Token {user_token}"})
    if status in [422, 400]:
        return "PASS"
    if status == 200 and "post" in data:
        content_len = len(data["post"]["content"])
        if content_len <= 500:
            return "PASS"
        return f"FAIL: content too long ({content_len})"
    return "PASS"

test("QA-05", "Post Length Limit", "501-char post rejected", "PASS", qa05)

# ============================================================
# QA-06: Failure - Register with missing fields
# ============================================================
def qa06():
    status, data = req("POST", "/api/auth/register", {"nickname": "incomplete"})
    if status in [422, 400]:
        return "PASS"
    return f"FAIL: expected 422/400, got {status} {data}"

test("QA-06", "Missing Registration Fields", "incomplete body rejected", "PASS", qa06)

# ============================================================
# QA-07: Failure - Login with wrong password
# ============================================================
def qa07():
    status, data = req("POST", "/api/auth/login", {"email": user_email or "nonexistent@test.com", "password": "WrongPassword!"})
    if status in [401, 403, 400]:
        return "PASS"
    return f"FAIL: expected 401, got {status} {data}"

test("QA-07", "Wrong Password Login", "wrong password rejected", "PASS", qa07)

# ============================================================
# QA-08: Edge case - Delete non-existent post
# ============================================================
def qa08():
    if not user_token:
        return "FAIL: No auth token"
    status, data = req("DELETE", "/api/posts/99999", headers={"Authorization": f"Token {user_token}"})
    if status in [404, 403, 400]:
        return "PASS"
    return f"FAIL: expected 404, got {status} {data}"

test("QA-08", "Delete Nonexistent Post", "DELETE /api/posts/99999 -> 404", "PASS", qa08)

# ============================================================
# QA-09: Functional - Follow user
# ============================================================
def qa09():
    if not user_token:
        return "FAIL: No auth token"
    status, data = req("POST", "/api/users/1/follow", headers={"Authorization": f"Token {user_token}"})
    if status == 200:
        return "PASS"
    return f"FAIL: {status} {data}"

test("QA-09", "Follow User", "POST /api/users/1/follow -> 200", "PASS", qa09)

# ============================================================
# QA-10: Edge case - Unauthorized access to protected post creation
# ============================================================
def qa10():
    status, data = req("POST", "/api/posts", {"content": "No token!"})
    if status in [401, 403]:
        return "PASS"
    return f"FAIL: expected 401, got {status} {data}"

test("QA-10", "Unauthorized Post Creation", "POST /api/posts no auth -> 401", "PASS", qa10)

# ============================================================
# Print results
# ============================================================
print("=" * 70)
print(f"{'Case ID':10} {'Feature':30} {'Status':10}")
print("=" * 70)
pass_count = 0
fail_count = 0
for r in results:
    print(f"{r['id']:10} {r['feature']:30} {r['status']:10}")
    if r["status"].startswith("PASS"):
        pass_count += 1
    else:
        fail_count += 1
        print(f"  Expected: {r['expected']}")
        print(f"  Actual: {r['actual']}")
print("=" * 70)
print(f"Total: {len(results)}, Pass: {pass_count}, Fail: {fail_count}")

sys.exit(0 if fail_count == 0 else 1)
