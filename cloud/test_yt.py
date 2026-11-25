import datetime as dt, json, os, tempfile, io, contextlib
import yt_upload as y
n = 0
def ok(c, m):
    global n; assert c, m; n += 1
T = dt.datetime(2026, 11, 28, 5, tzinfo=dt.timezone.utc); J = {"title": "Let it go", "description": "x #motivation", "when": "2026-12-01T05:00:00Z"}
b = y.body(J, T); ok(b["status"]["privacyStatus"] == "private" and b["status"]["publishAt"] == "2026-12-01T05:00:00Z", "never public"); ok(b["status"]["selfDeclaredMadeForKids"] is False, "kids"); ok(b["status"]["containsSyntheticMedia"] is False, "ai no")
ok(y.body({**J, "when": "2026-12-01T06:00:00+01:00"}, T)["status"]["publishAt"] == "2026-12-01T05:00:00Z", "lagos to utc")
for o in ({"when": "2026-11-28T05:10:00Z"}, {"when": "2026-11-27T05:00:00Z"}, {"when": "2027-01-01T05:00:00Z"}, {"when": "2026-12-01T05:00:00"}, {"title": ""}, {"title": "a" * 101}, {"title": "a<b"}, {"description": "a" * 5001}):
    try: y.body({**J, **o}, T); ok(False, o)
    except ValueError: ok(True, "")
f = tempfile.mktemp(); open(f, "wb").write(b"0" * 600_000); jf = tempfile.mktemp(); os.environ["YT_KEY"] = '{"client_id":"a","client_secret":"b","refresh_token":"c"}'
os.environ["BUFFER_KEY"] = os.environ["BUFFER_ORG"] = "x"
def world(titles=(), slots=(), channel=y.CHANNEL, back=None, when=None, buf=(), bufdown=False, other=()):
    when = when or (y.now() + dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:00Z"); json.dump({**J, "file": f, "when": when}, open(jf, "w")); calls = []
    def http(url, data=None, headers=None, method=None):
        calls.append((method, url)); R = lambda d: ({}, json.dumps(d).encode())
        if "buffer" in url: return R({"errors": ["down"]}) if bufdown else R({"data": {"channels": [{"id": "Y", "service": "youtube"}, {"id": "T", "service": "tiktok"}], "posts": {"pageInfo": {"hasNextPage": False}, "edges": [{"node": {"channelId": "Y", "dueAt": s}} for s in buf] + [{"node": {"channelId": "T", "dueAt": s}} for s in other]}}})
        if "oauth2" in url: return R({"access_token": "t"})
        if "channels?" in url: return R({"items": [{"id": channel, "contentDetails": {"relatedPlaylists": {"uploads": "U"}}}]})
        if "playlistItems" in url: return R({"items": [{"contentDetails": {"videoId": "v"}}]})
        if "uploadType" in url: ok("notifySubscribers=false" in url, "quiet"); return {"Location": "https://up/"}, b""
        if method == "PUT": return R({"id": "NEW"})
        if "id=NEW" in url: return R({"items": [{"status": back or {"privacyStatus": "private", "publishAt": when}}]})
        return R({"items": [{"snippet": {"title": t}, "status": {"publishAt": s}} for t, s in zip(list(titles) or ["old"], list(slots) or [""])]})
    y.http = http; return calls, when
def go(*a):
    o = io.StringIO()
    try:
        with contextlib.redirect_stdout(o): y.main([jf, *a])
    except SystemExit as e: return "STOP " + str(e)
    return o.getvalue()
put = lambda c: any(m == "PUT" for m, _ in c)
c, w = world(); ok("SCHEDULED NEW" in go() and put(c), "happy")
c, w = world(); ok("DRY ok" in go("--dry") and not put(c) and not any("uploadType" in u for _, u in c), "dry uploads nothing")
c, w = world(titles=["LET IT GO"]); ok("same title" in go() and not put(c), "duplicate title")
c, w = world(); c, w = world(titles=["other"], slots=[w], when=w); ok("slot already" in go() and not put(c), "taken slot")
c, w = world(channel="UCother"); ok("wrong channel" in go() and not put(c), "wrong channel")
c, w = world(back={"privacyStatus": "public"}); ok("does not match" in go(), "public read back is caught")
_, w = world(); c, w = world(buf=[w[:16] + ":00.000Z"], when=w); ok("slot already" in go() and not put(c), "slot held in Buffer")
_, w = world(); c, w = world(other=[w], when=w); ok("SCHEDULED" in go(), "a TikTok slot does not block YouTube")
c, w = world(bufdown=True); ok("Buffer could not" in go() and not put(c), "unreadable Buffer stops")
print(n, "checks PASS")
