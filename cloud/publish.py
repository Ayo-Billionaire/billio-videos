"""publish.py: schedule every reviewed, passed video in the next slot that is free on ALL three channels (00, 06, 12, 18 Lagos).
TikTok + Instagram go into the cloud refill list (Worker billionaire-refill feeds Buffer, 10 per channel cap). YouTube is uploaded
directly with a publish time (yt_upload.py). Never posts now, never stacks a slot, never posts the same job twice.
Env: DATA (data repo path), BUFFER_KEY, BUFFER_ORG, CF_ACCOUNT, CF_TOKEN, YT_KEY. --dry reads everything and changes nothing."""
import datetime as dt, glob, json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import yt_upload
UTC, LAGOS = dt.timezone.utc, dt.timezone(dt.timedelta(hours=1)); LEAD = dt.timedelta(hours=2)
NS = "0d1a574e1ba84c1b8d832bcff4ce7550"; MEDIA = "https://noqode-media.noqodepro.workers.dev/v/"
E_ = os.environ.get; DRY = "--dry" in sys.argv
def now(): return dt.datetime.now(UTC)
def parse(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC).replace(second=0, microsecond=0)
def iso(t): return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
def http(url, data=None, headers=None, method=None, timeout=120):
    r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", **(headers or {})}, method=method), timeout=timeout)
    return r.read()
def buf(q, v=None):
    d = json.loads(http("https://api.buffer.com", json.dumps({"query": q, "variables": v or {}}).encode(), {"Authorization": "Bearer " + E_("BUFFER_KEY"), "Content-Type": "application/json"}, "POST"))
    if d.get("errors") or not d.get("data"): raise SystemExit("Buffer error " + str(d.get("errors"))[:200])
    return d["data"]
def kv(key, data=None, method=None):
    u = f"https://api.cloudflare.com/client/v4/accounts/{E_('CF_ACCOUNT')}/storage/kv/namespaces/{NS}/values/" + urllib.parse.quote(key, safe="")
    return http(u, data, {"Authorization": "Bearer " + E_("CF_TOKEN"), "Content-Type": "application/octet-stream"}, method or ("PUT" if data is not None else "GET"), 300)
def refill_list():
    try: return json.loads(kv("vrefill:queue"))
    except urllib.error.HTTPError as e:
        if e.code == 404: return []
        raise
def channels():
    return {c["service"]: c["id"] for c in buf("query($i:ChannelsInput!){channels(input:$i){id service isDisconnected isLocked}}", {"i": {"organizationId": E_("BUFFER_ORG")}})["channels"] if not c["isDisconnected"] and not c["isLocked"]}
def busy(ch, yt_slots):
    b = set(yt_slots); after = ""
    while True:
        p = buf('{posts(first:100%s,input:{organizationId:%s,filter:{status:[scheduled,sending]}}){pageInfo{hasNextPage endCursor} edges{node{dueAt channelId}}}}' % (after, json.dumps(E_("BUFFER_ORG"))))["posts"]
        b |= {parse(e["node"]["dueAt"]) for e in p["edges"] if e["node"]["dueAt"] and e["node"]["channelId"] in ch.values()}
        if not p["pageInfo"]["hasNextPage"]: break
        after = ',after:"%s"' % p["pageInfo"]["endCursor"]
    b |= {parse(i["when"]) for i in refill_list()}
    return b
def next_slot(taken, at):
    t = at.astimezone(LAGOS).replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(400):
        if t >= at + LEAD and t.astimezone(UTC) not in taken: return t.astimezone(UTC)
        t += dt.timedelta(hours=6)
    raise SystemExit("no free slot in 100 days")
def captions(c):
    tags = " ".join("#" + t.lstrip("#").lower().replace(" ", "") for t in c["hashtags"])
    body = "\n".join(l for l in c["caption"].strip().splitlines() if not l.strip().startswith("#")).strip()
    social = f'{body}\n\n{tags}'
    return social, c["title"].strip(), f'{c["youtube_description"].strip()}\n\n{tags}', [t.lstrip("#") for t in c["hashtags"]]
def ready(data):
    out = []
    for d in sorted(glob.glob(data + "/jobs/*/")):
        st = json.load(open(d + "state.json")) if os.path.exists(d + "state.json") else {}
        rv = json.load(open(d + "review.json")) if os.path.exists(d + "review.json") else {}
        if st.get("stage") == "built" and rv.get("verdict") == "pass" and not os.path.exists(d + "published.json"): out.append(d)
    return out
def publish(d, slot, ch, video):
    n = open(d + "number.txt").read().strip(); c = json.load(open(d + "caption.json")); social, title, desc, tags = captions(c)
    slug = f"{n}-{c.get('slug', 'billio')}".lower(); slug = "".join(x for x in slug if x.isalnum() or x == "-")[:60] + ".mp4"
    if DRY: print("DRY", n, "->", slot.astimezone(LAGOS).strftime("%a %d %b %H:%M"), slug, len(social), "chars"); return None
    kv("vid:" + slug, open(video, "rb").read())
    got = len(http(MEDIA + slug, timeout=180))
    if got != os.path.getsize(video): raise SystemExit(f"media URL served {got} bytes, file is {os.path.getsize(video)}")
    base = {"schedulingType": "automatic", "mode": "customScheduled", "dueAt": iso(slot), "assets": [{"video": {"url": MEDIA + slug}}], "text": social}
    items = [{"id": slug[:-4] + ":tiktok", "platform": "tiktok", "when": iso(slot), "input": {**base, "channelId": ch["tiktok"]}},
             {"id": slug[:-4] + ":instagram", "platform": "instagram", "when": iso(slot), "input": {**base, "channelId": ch["instagram"], "metadata": {"instagram": {"type": "reel", "shouldShareToFeed": True}}}}]
    q = [i for i in refill_list() if parse(i["when"]) > now() and i["id"] not in {x["id"] for x in items}]
    kv("vrefill:queue", json.dumps(sorted(q + items, key=lambda i: (i["when"], i["id"]))).encode())
    back = {i["id"] for i in refill_list()}
    if not {x["id"] for x in items} <= back: raise SystemExit("refill list read back is missing the new items")
    job = {"file": video, "title": title, "description": desc, "tags": tags, "when": iso(slot)}
    json.dump(job, open(d + "yt.json", "w")); yt_upload.main([d + "yt.json"])
    rec = {"slot": iso(slot), "slug": slug, "at": iso(now())}; json.dump(rec, open(d + "published.json", "w"), indent=1); return rec
def record(data, d):
    """Make the writer see this video as published: spoken script and pictures."""
    k = open(d + "key.txt").read().strip(); n = open(d + "number.txt").read().strip(); lines = json.load(open(d + "opts.json"))[k]
    p = json.load(open(data + "/writer/published.json")); p["spoken"][f"{n}-cloud"] = " ".join(lines); json.dump(p, open(data + "/writer/published.json", "w"), indent=0)
    cat = json.load(open(data + "/pool/catalog.json"))
    for i in json.load(open(d + "picks.json")).values():
        if i in cat and n not in cat[i]["used"]: cat[i]["used"].append(n)
    json.dump(cat, open(data + "/pool/catalog.json", "w"), indent=0)
    u = json.load(open(data + "/writer/used-episodes.json")); e = json.load(open(d + "source.json")).get("episode")
    if e is not None and int(e) not in u: u.append(int(e)); json.dump(sorted(u), open(data + "/writer/used-episodes.json", "w"))
def cleanup(data):
    """Delete hosted video files two days after their slot (KV free space is 1 GB)."""
    for f in glob.glob(data + "/jobs/*/published.json"):
        r = json.load(open(f))
        if not r.get("cleaned") and parse(r["slot"]) < now() - dt.timedelta(days=2):
            if not DRY: kv("vid:" + r["slug"], method="DELETE"); r["cleaned"] = iso(now()); json.dump(r, open(f, "w"), indent=1)
            print("cleaned", r["slug"])
def main():
    data = E_("DATA"); todo = ready(data); cleanup(data)
    if not todo: print("nothing to publish"); return
    ch = channels()
    if not {"tiktok", "instagram"} <= set(ch): raise SystemExit("TikTok or Instagram missing or locked in Buffer")
    h = {"Authorization": "Bearer " + yt_upload.token(json.loads(E_("YT_KEY")))}; titles, ys = yt_upload.existing(h)
    taken = busy(ch, {parse(s + ":00Z") for s in ys})
    for d in todo[:4]:
        video = d + "result/test.mp4"
        if not os.path.exists(video): print("no video file for", d); continue
        slot = next_slot(taken, now()); rec = publish(d, slot, ch, video); taken.add(slot)
        if rec: record(data, d); print("SCHEDULED", open(d + "number.txt").read().strip(), slot.astimezone(LAGOS).strftime("%a %d %b %H:%M Lagos"))
if __name__ == "__main__": main()
