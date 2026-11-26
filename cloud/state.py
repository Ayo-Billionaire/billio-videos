"""state.py <data> <job> <built|failed|fixapply> [reason]: record a stage in jobs/<job>/state.json (and apply a reviewer fix)."""
import datetime as dt, json, os, sys
D, j, what = sys.argv[1:4]; d = f"{D}/jobs/{j}/"; now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
st = json.load(open(d + "state.json")) if os.path.exists(d + "state.json") else {}
if what == "fixapply":
    rv = json.load(open(d + "review.json")); art = json.load(open(d + "art.json")) if os.path.exists(d + "art.json") else {}
    for k, v in rv.get("art", {}).items(): art.setdefault(k, {}).update(v)
    json.dump(art, open(d + "art.json", "w"))
    if rv.get("picks"): pk = json.load(open(d + "picks.json")); pk.update(rv["picks"]); json.dump(pk, open(d + "picks.json", "w"))
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
        if rv.get("verdict") == "fix" and rv.get("applied"): os.rename(d + "review.json", d + f"review-{st.get('fixed', 1)}.json")
json.dump(st, open(d + "state.json", "w"), indent=1); print(j, st["stage"])
