#!/bin/bash
# render.sh <job>: builds data/jobs/<job> with the kit. Public log: step names, pass or fail and numbers only, never script text.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || { echo "bad job id"; exit 1; }
export HYPERFRAMES_NO_TELEMETRY=1
cd data; J="jobs/$1"; [ -d "$J" ] || { echo "no such job"; exit 1; }
K="$RUNNER_TEMP/kit"; cp -R kit "$K"; P="inq-format4-$1"; cp -R "$J" "$K/$P"; cd "$K"; R="$GITHUB_WORKSPACE/data/jobs/$1/result"; mkdir -p "$R"
TAG=$(cat "$P/tag.txt")
step() { local n="$1"; shift; if "$@" > "$R/$n.log" 2>&1; then echo "ok   $n"; else echo "FAIL $n"; exit 1; fi; }
step plan python3 _format-4-tools/make_gen.py "$P" "$TAG" "$P/plan.json"
cd "$P"; step page python3 gen.py
step render npx --yes hyperframes@0.8.230 render . --output test.mp4
cp test.mp4 "$R/test.mp4"
sed -i 's#/System/Library/Fonts/Supplemental/Arial Bold.ttf#/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf#' verify/sheets.py
step sheets python3 verify/sheets.py test.mp4
cp verify/sheet-*.jpg "$R/"; cd ..
step pace python3 _format-4-tools/inq_match.py "$P"
step sound python3 _signature-sound/check_sound.py "$P"
grep -q 'RESULT: PASS' "$R/pace.log" && grep -q 'RESULT: PASS' "$R/sound.log" || { echo "FAIL checks"; exit 1; }
ffprobe -v error -show_entries format=duration -of csv=p=0 "$R/test.mp4" | sed 's/^/seconds /'
if [ -f "$P/approved.mp4" ]; then ffmpeg -v info -i "$R/test.mp4" -i "$P/approved.mp4" -lavfi "[0:v][1:v]ssim" -f null - 2>&1 | grep -oE 'All:[0-9.]+' | tail -1 | sed 's/^/ssim /'; fi
echo PASS > "$R/status.txt"
