"""state.py <data> <job> <built|failed|fixapply> [reason]: record a stage in jobs/<job>/state.json (and apply a reviewer fix)."""
import datetime as dt, json, os, sys
D, j, what = sys.argv[1:4]; d = f"{D}/jobs/{j}/"; now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
st = json.load(open(d + "state.json")) if os.path.exists(d + "state.json") else {}
if what == "fixapply":
    rv = json.load(open(d + "review.json")); art = json.load(open(d + "art.json")) if os.path.exists(d + "art.json") else {}
    for k, v in rv.get("art", {}).items(): art.setdefault(k, {}).update(v)
    json.dump(art, open(d + "art.json", "w"))
    if rv.get("picks"): pk = json.load(open(d + "picks.json")); cat = json.load(open(os.path.dirname(os.path.dirname(d.rstrip("/"))) + "/pool/catalog.json")); pk.update({k: v for k, v in rv["picks"].items() if v in cat and 0 < cat[v].get("bytes", 0) <= 1_900_000}); json.dump(pk, open(d + "picks.json", "w"))   # a swap over the 2 MB build limit is skipped, the old picture stays
    if rv.get("plan_colours"):
        pf = d + "plan.final.json"
        if os.path.exists(pf):
            pl = json.load(open(pf))
            for k, c in rv["plan_colours"].items(): pl[int(k) - 1][5] = c
            json.dump(pl, open(pf, "w"))
        else: json.dump(rv["plan_colours"], open(d + "colours.json", "w"))
    rv["applied"] = True; json.dump(rv, open(d + "review.json", "w"), indent=1); st.update(stage="ready", fixed=st.get("fixed", 0) + 1)
else:
    st.update(stage=what, at=now); st["reason"] = sys.argv[4][:300] if len(sys.argv) > 4 else ""
    if what == "built" and os.path.exists(d + "review.json"):
        rv = json.load(open(d + "review.json"))
        # record.sh resets to origin/main first, so the "applied" mark from the fix step is gone here: a fix review that
        # reached a successful build is always retired, or plan.py rebuilds the same fix every hour (it did, 26 Nov).
        if rv.get("verdict") == "fix":
            st["fixed"] = st.get("fixed", 0) + 1; rv["applied"] = True
            json.dump(rv, open(d + f"review-{st['fixed']}.json", "w"), indent=1); os.remove(d + "review.json")
json.dump(st, open(d + "state.json", "w"), indent=1); print(j, st["stage"])
