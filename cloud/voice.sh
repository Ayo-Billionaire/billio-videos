#!/bin/bash
# voice.sh <job>: signature voice, mix and word times for data/jobs/<job>. Public log: line numbers, scores, pass or fail. Never script text.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || { echo "bad job id"; exit 1; }
HERE="$GITHUB_WORKSPACE/cloud"; J="$GITHUB_WORKSPACE/data/jobs/$1"; [ -d "$J" ] || { echo "no such job"; exit 1; }
R="$J/result"; mkdir -p "$R"; K="$RUNNER_TEMP/kit"; cp -R "$GITHUB_WORKSPACE/data/kit" "$K"; KEY=$(cat "$J/key.txt"); TAG=$(cat "$J/tag.txt")
G="$RUNNER_TEMP/gen"; mkdir -p "$G"; cp "$K/_signature-sound/spec.json" "$K/_signature-sound/assets/michael-ref.wav" "$G/"; cp "$J/opts.json" "$G/lines.json"; echo '{}' > "$G/seeds.json"; [ -f "$J/seeds.json" ] && cp "$J/seeds.json" "$G/seeds.json"
(cd "$G" && python "$HERE/voice_gen.py" "$KEY" > "$R/gen.log" 2>&1) || { echo "FAIL voice"; exit 1; }
grep -oE '^L[0-9]+ seed [0-9]+ score [0-9.]+$' "$R/gen.log" || true
N=$(python -c "import json,sys;print(len(json.load(open(sys.argv[1]))[sys.argv[2]]))" "$J/opts.json" "$KEY")
cp "$G/out/report_$KEY.json" "$R/report.json"
python "$K/voice_post.py" "$G/out" "$R/signature-lines" "$N" > "$R/post.log" 2>&1 || { echo "FAIL post"; exit 1; }
cd "$K"; mkdir -p _lipsync-v3/venv/bin; ln -s "$(command -v python)" _lipsync-v3/venv/bin/python
P="inq-format4-$1"; mkdir -p "$P"
python _format-4-tools/build_audio.py "$P" "$R/signature-lines" "$J/opts.json" "$KEY" "$TAG" > "$R/audio.log" 2>&1 || { echo "FAIL audio"; exit 1; }
cp -R "$P/assets" "$P/verify" "$R/"; python _signature-sound/check_sound.py "$P" > "$R/sound.log" 2>&1 || true
grep -q 'RESULT: PASS' "$R/sound.log" && echo "ok   sound" || echo "FAIL sound"
python - "$R/report.json" <<'P'
import json, sys
r = json.load(open(sys.argv[1])); bad = [k for k, v in r.items() if v["score"] < 0.97]; print("lines", len(r), "below 0.97:", bad or "none")
P
grep -q 'RESULT: PASS' "$R/sound.log" && echo PASS > "$R/status.txt"
