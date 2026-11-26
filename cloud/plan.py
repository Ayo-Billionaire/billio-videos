"""plan.py <data>: print the job id to build now, or nothing. A job is built when the writer marked it ready (state.json stage ready)
or the reviewer asked for a fix (review.json verdict fix, at most 2 rounds). STOP file in the data repo stops everything."""
import glob, json, os, sys
D = sys.argv[1]
if os.path.exists(D + "/STOP"): sys.exit(0)
for d in sorted(glob.glob(D + "/jobs/*/")):
    j = os.path.basename(d.rstrip("/"))
    st = json.load(open(d + "state.json")) if os.path.exists(d + "state.json") else {}
    rv = json.load(open(d + "review.json")) if os.path.exists(d + "review.json") else {}
    if st.get("stage") == "ready" or (st.get("stage") == "built" and rv.get("verdict") == "fix" and rv.get("round", 1) <= 2 and rv.get("applied") != True):
        print(j); break
