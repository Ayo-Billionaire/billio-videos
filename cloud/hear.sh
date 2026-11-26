#!/bin/bash
# hear.sh <job>: the script's lines against the episode audio. Public log: line numbers and scores only.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || { echo "bad job id"; exit 1; }
D="$GITHUB_WORKSPACE/data"; J="$D/jobs/$1"; mkdir -p "$J/result"
python "$D/kit/hear.py" "$J" "$D/writer/index.json" "$D/writer/timing" 2>"$J/result/hear.err" || { tail -c 300 "$J/result/hear.err" | grep -oE 'FAIL[^"]*' | head -1; echo "FAIL hear"; exit 1; }
echo "ok   hear"
