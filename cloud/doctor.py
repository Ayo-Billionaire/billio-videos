"""doctor.py <data>: runs at the start of every hourly run and clears stuck jobs, so the channel never stalls with nobody watching.
1. failed for a reason that can be a one off (anything but the hear check, which means the script itself is wrong): built again once.
2. built with a review that will never let it post (verdict fail, or a fix after the last allowed round): marked failed, so the
   writer no longer counts it as stock and writes a new video in its place.
Prints one line per change. The alert email still goes out for the failure itself."""
import datetime as dt, glob, json, os, sys
D = sys.argv[1]; now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
if os.path.exists(D + "/STOP"): sys.exit(0)
for d in sorted(glob.glob(D + "/jobs/*/")):
    j = os.path.basename(d.rstrip("/")); f = d + "state.json"
    if not os.path.exists(f) or os.path.exists(d + "published.json"): continue
    st = json.load(open(f)); rv = json.load(open(d + "review.json")) if os.path.exists(d + "review.json") else {}
    stage, why = st.get("stage"), st.get("reason", "")
    if stage == "failed" and st.get("retried", 0) < 1 and not why.startswith("hear"):
        back = "built" if rv.get("verdict") == "fix" and not rv.get("applied") and os.path.exists(d + "picks.json") and st.get("at") else "ready"
        if back == "built" and not glob.glob(d + "review*.json"): back = "ready"
        st.update(stage=back, retried=st.get("retried", 0) + 1, reason="", at=now); print(j, "retry after", why or "failure", "->", back)
    elif stage == "built" and rv.get("verdict") == "fail":
        st.update(stage="failed", reason="review: fail", at=now, retried=1); print(j, "review fail -> failed")
    elif stage == "built" and rv.get("verdict") == "fix" and (rv.get("round", 1) > 2 or rv.get("applied")):
        st.update(stage="failed", reason="review: more fixes than allowed", at=now, retried=1); print(j, "fix after the last round -> failed")
    else: continue
    json.dump(st, open(f, "w"), indent=1)
