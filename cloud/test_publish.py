import datetime as dt, json, os, shutil, tempfile
os.environ.update(BUFFER_KEY="k", BUFFER_ORG="o", CF_ACCOUNT="a", CF_TOKEN="t", YT_KEY='{"client_id":"a","client_secret":"b","refresh_token":"c"}')
import publish as p
n = 0
def ok(c, m):
    global n; assert c, m; n += 1
L = p.LAGOS; at = dt.datetime(2026, 11, 26, 7, 0, tzinfo=dt.timezone.utc)
ok(p.next_slot(set(), at) == dt.datetime(2026, 11, 26, 11, tzinfo=dt.timezone.utc), "next is 12:00 Lagos")
ok(p.next_slot({dt.datetime(2026, 11, 26, 11, tzinfo=dt.timezone.utc)}, at) == dt.datetime(2026, 11, 26, 17, tzinfo=dt.timezone.utc), "taken skipped")
ok(p.next_slot(set(), dt.datetime(2026, 11, 26, 9, 30, tzinfo=dt.timezone.utc)) == dt.datetime(2026, 11, 26, 17, tzinfo=dt.timezone.utc), "under 2 h is too close")
s, t, d, tags = p.captions({"caption": "Watch this if x.\n\nLine.", "title": "T", "youtube_description": "D", "hashtags": ["#Motivation", "self improvement"]})
ok(s.endswith("#motivation #selfimprovement") and t == "T" and tags == ["Motivation", "self improvement"], "captions")
root = tempfile.mkdtemp(); data = root + "/data"; os.makedirs(data + "/writer"); os.makedirs(data + "/pool")
json.dump({"spoken": {}, "captions": {}}, open(data + "/writer/published.json", "w")); json.dump([1], open(data + "/writer/used-episodes.json", "w")); json.dump({"Q:1": {"used": []}}, open(data + "/pool/catalog.json", "w"))
def job(num, stage="built", verdict="pass", pub=False):
    d = f"{data}/jobs/{num}/"; os.makedirs(d + "result", exist_ok=True)
    json.dump({"stage": stage}, open(d + "state.json", "w")); json.dump({"verdict": verdict}, open(d + "review.json", "w"))
    open(d + "number.txt", "w").write(str(num)); open(d + "key.txt", "w").write(str(num)); json.dump({str(num): ["a b c"]}, open(d + "opts.json", "w"))
    json.dump({"s01": "Q:1"}, open(d + "picks.json", "w")); json.dump({"episode": 5}, open(d + "source.json", "w"))
    json.dump({"caption": "Watch this if x.", "title": "T", "youtube_description": "D", "hashtags": ["a"], "slug": "x"}, open(d + "caption.json", "w"))
    open(d + "result/test.mp4", "wb").write(b"0" * 900_000)
    if pub: json.dump({"slot": "2026-11-20T05:00:00.000Z", "slug": "9-x.mp4"}, open(d + "published.json", "w"))
job(140); job(141, verdict="fail"); job(142, stage="failed"); job(143, pub=True); job(144, stage="ready")
ok([os.path.basename(x.rstrip("/")) for x in p.ready(data)] == ["140"], "only built + passed + unpublished")
kvs, calls, ups = {}, [], []
def http(url, data=None, headers=None, method=None, timeout=120):
    calls.append((method, url))
    if "storage/kv" in url:
        k = p.urllib.parse.unquote(url.split("/values/")[1])
        if method == "PUT": kvs[k] = data; return b"{}"
        if method == "DELETE": kvs.pop(k, None); return b"{}"
        if k in kvs: return kvs[k]
        raise p.urllib.error.HTTPError(url, 404, "", {}, None)
    if url.startswith(p.MEDIA): return kvs["vid:" + url[len(p.MEDIA):]]
    if "buffer" in url:
        q = json.loads(data)["query"]
        if "channels" in q: return json.dumps({"data": {"channels": [{"id": "T", "service": "tiktok", "isDisconnected": False, "isLocked": False}, {"id": "I", "service": "instagram", "isDisconnected": False, "isLocked": False}]}}).encode()
        return json.dumps({"data": {"posts": {"pageInfo": {"hasNextPage": False}, "edges": [{"node": {"dueAt": "2026-11-26T11:00:00.000Z", "channelId": "T"}}]}}}).encode()
p.http = http
p.yt_upload.token = lambda k: "tok"; p.yt_upload.existing = lambda h: (set(), {"2026-11-26T17:00"}); p.yt_upload.main = lambda a: ups.append(json.load(open(a[0])))
p.now = lambda: at; os.environ["DATA"] = data; kvs["vid:9-x.mp4"] = b"x"
p.main()
q = json.loads(kvs["vrefill:queue"]); r = json.load(open(data + "/jobs/140/published.json"))
ok(r["slot"] == "2026-11-26T23:00:00.000Z", "skips Buffer 12:00 and YouTube 18:00, takes 00:00 Lagos")
ok({i["platform"] for i in q} == {"tiktok", "instagram"} and all(i["when"] == r["slot"] for i in q), "refill items, same slot")
ok(ups and ups[0]["when"] == r["slot"], "YouTube same slot"); ok("vid:140-x.mp4" in kvs, "video hosted")
ok("140-cloud" in json.load(open(data + "/writer/published.json"))["spoken"] and "140" in json.load(open(data + "/pool/catalog.json"))["Q:1"]["used"] and 5 in json.load(open(data + "/writer/used-episodes.json")), "recorded")
before = len(ups); p.main(); ok(len(ups) == before, "no double publish")
ok("vid:9-x.mp4" not in kvs and json.load(open(data + "/jobs/143/published.json")).get("cleaned"), "old video cleaned")
job(150); p.yt_upload.main = lambda a: (_ for _ in ()).throw(SystemExit("yt failed")); 
try: p.main(); ok(False, "should stop")
except SystemExit: ok(not os.path.exists(data + "/jobs/150/published.json"), "a failed upload is not recorded as published")
# two ready at once + a slot held in the refill list
p.yt_upload.main = lambda a: ups.append(json.load(open(a[0])))
kvs["vrefill:queue"] = json.dumps([{"id": "z:tiktok", "platform": "tiktok", "when": "2026-11-27T05:00:00.000Z"}]).encode()
job(160); job(161); p.main()
a1, a2 = json.load(open(data + "/jobs/160/published.json"))["slot"], json.load(open(data + "/jobs/161/published.json"))["slot"]
ok(a1 == "2026-11-27T11:00:00.000Z" and a2 == "2026-11-27T17:00:00.000Z", f"refill slot respected and two videos get two slots {a1} {a2}")
# wrong size served
job(170); real = p.http
p.http = lambda url, *a, **k: b"short" if url.startswith(p.MEDIA) else real(url, *a, **k)
try: p.main(); ok(False, "size")
except SystemExit as e: ok("bytes" in str(e) and not os.path.exists(data + "/jobs/170/published.json"), "wrong size stops")
# refill list that does not save
def lossy(url, data=None, headers=None, method=None, timeout=120):
    if "vrefill" in url and method == "PUT": return b"{}"
    return real(url, data, headers, method, timeout)
p.http = lossy
try: p.main(); ok(False, "readback")
except SystemExit as e: ok("read back" in str(e) and not os.path.exists(data + "/jobs/170/published.json"), "lost refill write stops")
p.http = real
print(n, "checks PASS"); shutil.rmtree(root)
