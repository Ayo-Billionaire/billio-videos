"""alerts.py <data>: email Ayo only when something needs him. Each alert once a day at most. Env BREVO_KEY, ALERT_FROM, ALERT_TO."""
import datetime as dt, glob, json, os, sys, urllib.request
D = sys.argv[1]; now = dt.datetime.now(dt.timezone.utc); E = os.environ.get; A = D + "/alerts.json"
seen = json.load(open(A)) if os.path.exists(A) else {}
def p(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
msgs = []
def say(key, text, every_h=24):
    last = seen.get(key)
    if last and now - p(last) < dt.timedelta(hours=every_h): return
    msgs.append(text); seen[key] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
jobs = {os.path.basename(d.rstrip("/")): d for d in glob.glob(D + "/jobs/*/")}
st = lambda d: json.load(open(d + "state.json")) if os.path.exists(d + "state.json") else {}
for j, d in jobs.items():
    s = st(d)
    if s.get("stage") == "failed": say("failed:" + j, f"Video job {j} failed to build ({s.get('reason') or 'see the GitHub run'}). It was dropped, nothing was posted.", 24 * 365)
future = [json.load(open(f))["slot"] for f in glob.glob(D + "/jobs/*/published.json")]
ahead = sum(1 for s in future if p(s) > now); stock = sum(1 for d in jobs.values() if st(d).get("stage") in ("ready", "built") and not os.path.exists(d + "published.json"))
if ahead + stock < 8: say("stock", f"Only {ahead} videos are scheduled ahead and {stock} are being made. Less than two days of videos left.")
newest = max([p(st(d)["created"]) for d in jobs.values() if st(d).get("created")] or [now - dt.timedelta(days=99)])
if os.path.exists(D + "/writer/RULES.md") and now - newest > dt.timedelta(hours=36): say("writer", "The script writer has not added a video for over 36 hours. Check the Claude routine 'Billionaire video writer'.")
cat = json.load(open(D + "/pool/catalog.json")); free = sum(1 for c in cat.values() if not c["used"])
if free < 300: say("pictures", f"Only {free} unused pictures left. The weekly picture job should add more; check the 'pictures' GitHub job.", 24 * 3)
if os.environ.get("RUN_FAILED") == "1": say("run", "The hourly video pipeline failed. Look at the latest 'pipeline' run on GitHub (billio-videos).", 6)
if msgs and not os.path.exists(D + "/STOP"):
    body = {"sender": {"email": E("ALERT_FROM"), "name": "Billionaire videos"}, "to": [{"email": E("ALERT_TO")}], "subject": "Billionaire videos: " + ("1 problem" if len(msgs) == 1 else f"{len(msgs)} problems"), "textContent": "\n\n".join(f"{n+1}. {m}" for n, m in enumerate(msgs)) + "\n\nTo stop everything, ask Claude to add the STOP file to billio-data."}
    if os.environ.get("SANDBOX") == "1": body["headers"] = {"X-Sib-Sandbox": "drop"}
    r = urllib.request.urlopen(urllib.request.Request("https://api.brevo.com/v3/smtp/email", json.dumps(body).encode(), {"api-key": E("BREVO_KEY"), "content-type": "application/json", "accept": "application/json"}), timeout=60)
    print("alert sent", r.status, len(msgs))
json.dump(seen, open(A, "w"), indent=1); print("alerts checked", len(msgs))
