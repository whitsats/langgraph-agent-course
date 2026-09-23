import urllib.request, urllib.error, json, sys, random
R = []
T = None
def q(m, p, b=None, h=None):
    if h is None: h = {}
    if b is not None: h['Content-Type'] = 'application/json'
    d = json.dumps(b).encode() if b else None
    o = urllib.request.Request('http://localhost:8000'+p, data=d, headers=h, method=m)
    try:
        r = urllib.request.urlopen(o, timeout=10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return -1, str(e)

def record(cid, feat, ok):
    R.append((cid, feat, ok))

s, d = q('GET', '/health')
record('QA-01', 'Backend Health', s == 200 and d.get('status') == 'ok')

rs = random.randint(10000, 99999)
s, d = q('POST', '/api/auth/register', {'nickname': 'u1', 'email': 'a'+str(rs)+'@b.com', 'password': 'P123!'})
record('QA-02', 'User Registration', s == 200 and 'token' in d)

rs = random.randint(10000, 99999)
em = 'f'+str(rs)+'@g.com'
s, d = q('POST', '/api/auth/register', {'nickname': 'U'+str(rs), 'email': em, 'password': 'Test123!'})
if s == 200:
    T = d['token']
    q('POST', '/api/auth/logout', headers={'Authorization': 'Token '+T})
    s, d = q('POST', '/api/auth/login', {'email': em, 'password': 'Test123!'})
    if s == 200: T = d['token']
    record('QA-03', 'Auth Flow (login)', s == 200 and 'token' in d)
else:
    record('QA-03', 'Auth Flow (login)', False)

if T:
    s, d = q('POST', '/api/posts', {'content': 'RedTeam test'}, {'Authorization': 'Token '+T})
    record('QA-04', 'Create Post', s == 200 and 'post' in d)
else:
    record('QA-04', 'Create Post', False)

if T:
    s, d = q('POST', '/api/posts', {'content': 'X'*501}, {'Authorization': 'Token '+T})
    ok = s in [422, 400] or (s == 200 and len(d.get('post', {}).get('content', '')) <= 500)
    record('QA-05', 'Post >500 chars', ok)
else:
    record('QA-05', 'Post >500 chars', False)

s, d = q('POST', '/api/auth/register', {'nickname': 'x'})
record('QA-06', 'Missing Fields', s in [422, 400])

s, d = q('POST', '/api/auth/login', {'email': 'x@y.com', 'password': 'wrong'})
record('QA-07', 'Wrong Password', s in [401, 403, 400])

if T:
    s, d = q('DELETE', '/api/posts/99999', headers={'Authorization': 'Token '+T})
    record('QA-08', 'Delete Non-Existent', s in [404, 403, 400])
else:
    record('QA-08', 'Delete Non-Existent', False)

if T:
    s, d = q('POST', '/api/users/1/follow', headers={'Authorization': 'Token '+T})
    record('QA-09', 'Follow User', s == 200)
else:
    record('QA-09', 'Follow User', False)

s, d = q('POST', '/api/posts', {'content': 'noauth'})
record('QA-10', 'No Auth Post', s in [401, 403])

pc = sum(1 for r in R if r[2])
fc = sum(1 for r in R if not r[2])
print('='*70)
print('{:<10} {:<25} {:<10}'.format('Case ID', 'Feature', 'Status'))
print('='*70)
for r in R:
    print('{:<10} {:<25} {:<10}'.format(r[0], r[1], 'PASS' if r[2] else 'FAIL'))
print('='*70)
print('Total: {} | Pass: {} | Fail: {}'.format(len(R), pc, fc))
sys.exit(0 if fc == 0 else 1)
