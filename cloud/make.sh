#!/bin/bash
# make.sh <job>: script + spec + picks -> finished video. Public log: step names, scores, pass or fail. Never script text.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || { echo "bad job id"; exit 1; }
HERE="$GITHUB_WORKSPACE/cloud"; D="$GITHUB_WORKSPACE/data"; J="$D/jobs/$1"; R="$J/result"
bash "$HERE/voice.sh" "$1"
grep -q PASS "$R/status.txt" || { echo "FAIL voice checks"; exit 1; }
rm "$R/status.txt"   # only the finished video may say PASS
step() { local n="$1"; shift; if "$@" > "$R/$n.log" 2>&1; then echo "ok   $n"; else echo "FAIL $n"; exit 1; fi; }
cp -R "$D/kit/base/ref" "$D/kit/base/motion-pick.md" "$J/"; cp -R "$R/assets" "$J/"; cp -R "$R/verify" "$J/"; cp -R "$D/kit/base/assets/." "$J/assets/"; cp "$D/kit/base/verify/sheets.py" "$J/verify/"; cp -R "$R/signature-lines" "$J/verify/"
KEEP=""; [ -f "$J/art.json" ] && KEEP=1 && cp "$J/art.json" "$RUNNER_TEMP/art.json"
cp "$J/picks.json" "$J/picks.chosen.json"
step scenes python "$D/kit/_build/apply.py" "$J" "$J/spec.txt"
[ -n "$KEEP" ] && cp "$RUNNER_TEMP/art.json" "$J/art.json"; [ -f "$J/plan.final.json" ] && cp "$J/plan.final.json" "$J/plan.json"
python - "$J" <<'P'
import json, sys
j = sys.argv[1]; a, b = set(json.load(open(j + "/scenes-kw.json"))), set(json.load(open(j + "/picks.json")))
if a != b: sys.exit("FAIL picks do not match scenes: %d vs %d" % (len(a), len(b)))
print("scenes", len(a))
P
step pictures python "$D/kit/_build/extract.py" "$J/picks.json" "$D/pool/catalog.json" "$J" "$(cat "$J/number.txt")"
rm -rf "$R/assets" "$R/verify" "$R/signature-lines"
bash "$HERE/render.sh" "$1"
