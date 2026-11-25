"""Upload one approved video to the Billionaire YouTube channel as a SCHEDULED Short. Fixed code holds the key, no AI agent does.
Usage: yt_upload.py <job.json> [--dry]   job.json = {"file","title","description","tags":[],"when":"2026-12-01T05:00:00Z"}
Env YT_KEY = the json saved by yt_auth.py, BUFFER_KEY, BUFFER_ORG (read only here). Never uploads public: private + publishAt, then reads back. Prints ids and states only."""
import datetime as dt, json, os, sys, urllib.parse, urllib.request
CHANNEL = "UC4vyHZGq9AWfUFmPy2vu2cw"; API = "https://www.googleapis.com/youtube/v3/"
now = lambda: dt.datetime.now(dt.timezone.utc)
def http(url, data=None, headers=None, method=None):
    r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers or {}, method=method), timeout=300); return r.headers, r.read()
def body(job, at=None):
    at = at or now(); when = dt.datetime.fromisoformat(job["when"].replace("Z", "+00:00"))
    if when.tzinfo is None: raise ValueError("when needs a time zone")
    if when < at + dt.timedelta(minutes=30): raise ValueError("slot too close or passed")
    if when > at + dt.timedelta(days=14): raise ValueError("slot more than 14 days away")
    t, d = job["title"].strip(), job["description"].strip()
    if not t or len(t) > 100 or "<" in t + d or ">" in t + d: raise ValueError("bad title or description")
    if len(d.encode()) > 5000: raise ValueError("description too long")
    return {"snippet": {"title": t, "description": d, "tags": job.get("tags", []), "categoryId": "22"},
            "status": {"privacyStatus": "private", "publishAt": when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}}
def token(k):
    return json.loads(http("https://oauth2.googleapis.com/token", urllib.parse.urlencode({"client_id": k["client_id"], "client_secret": k["client_secret"], "refresh_token": k["refresh_token"], "grant_type": "refresh_token"}).encode())[1])["access_token"]
def get(path, h): return json.loads(http(API + path, headers=h)[1])
def existing(h):
    """Titles and publish times already on the channel: newest 50 uploads, private scheduled ones included."""
    ch = get("channels?part=contentDetails&mine=true", h)["items"]
    if [c["id"] for c in ch] != [CHANNEL]: raise SystemExit("wrong channel, stopped")
    ids = [i["contentDetails"]["videoId"] for i in get("playlistItems?part=contentDetails&maxResults=50&playlistId=" + ch[0]["contentDetails"]["relatedPlaylists"]["uploads"], h)["items"]]
    v = get("videos?part=snippet,status&id=" + ",".join(ids), h)["items"] if ids else []
    return {i["snippet"]["title"].strip().lower() for i in v}, {i["status"].get("publishAt", "")[:16] for i in v} - {""}
def buffer_slots():
    """YouTube slots still waiting inside the Billionaire Buffer, which YouTube itself cannot see."""
    q = "query{channels(input:{organizationId:%s}){id service} posts(first:100,input:{organizationId:%s,filter:{status:[scheduled,sending]}}){pageInfo{hasNextPage} edges{node{channelId dueAt}}}}" % ((json.dumps(os.environ["BUFFER_ORG"]),) * 2)
    d = json.loads(http("https://api.buffer.com", json.dumps({"query": q}).encode(), {"Authorization": "Bearer " + os.environ["BUFFER_KEY"], "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, "POST")[1])
    if d.get("errors") or not d.get("data"): raise SystemExit("Buffer could not be read, stopped")
    d = d["data"]
    if d["posts"]["pageInfo"]["hasNextPage"]: raise SystemExit("more Buffer posts than one page, stopped")
    yt = {c["id"] for c in d["channels"] if c["service"] == "youtube"}
    if not yt: raise SystemExit("no YouTube channel in Buffer, stopped")
    return {e["node"]["dueAt"][:16] for e in d["posts"]["edges"] if e["node"]["channelId"] in yt and e["node"]["dueAt"]}
def main(args):
    job = json.load(open(args[0])); b = body(job); size = os.path.getsize(job["file"])
    if not 500_000 < size < 100_000_000: raise SystemExit("file size looks wrong")
    h = {"Authorization": "Bearer " + token(json.loads(os.environ["YT_KEY"]))}
    titles, slots = existing(h)
    slots |= buffer_slots()
    if b["snippet"]["title"].lower() in titles: raise SystemExit("same title already on the channel, stopped")
    if b["status"]["publishAt"][:16] in slots: raise SystemExit("slot already taken on the channel, stopped")
    if "--dry" in args: print("DRY ok", b["status"]["publishAt"], size, "bytes,", len(titles), "titles and", len(slots), "slots read"); return
    hd, _ = http("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status&notifySubscribers=false", json.dumps(b).encode(), {**h, "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}, "POST")
    vid = json.loads(http(hd["Location"], open(job["file"], "rb").read(), {**h, "Content-Type": "video/mp4"}, "PUT")[1])["id"]
    s = get("videos?part=status&id=" + vid, h)["items"][0]["status"]
    if s["privacyStatus"] != "private" or s.get("publishAt", "")[:16] != b["status"]["publishAt"][:16]: raise SystemExit(f"uploaded {vid} but read back does not match: {s}")
    print("SCHEDULED", vid, s["publishAt"])
if __name__ == "__main__": main(sys.argv[1:])
