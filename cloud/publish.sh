#!/bin/bash
# publish.sh: fetch each passed video from its result branch, schedule it, commit the records.
set -euo pipefail
cd "$GITHUB_WORKSPACE/data"; git pull -q --rebase origin main
for d in jobs/*/; do j=$(basename "$d")
  if [ -f "$d/review.json" ] && grep -q '"verdict": *"pass"' "$d/review.json" && [ ! -f "$d/published.json" ] && grep -q '"stage": *"built"' "$d/state.json" 2>/dev/null; then
    mkdir -p "$d/result"; git fetch -q origin "out-$j" && git show "origin/out-$j:jobs/$j/result/test.mp4" > "$d/result/test.mp4" && git show "origin/out-$j:jobs/$j/result/status.txt" | grep -q PASS || { echo "no passed video for $j"; rm -f "$d/result/test.mp4"; }
  fi
done
cd "$GITHUB_WORKSPACE"; python cloud/publish.py; bash cloud/commit.sh "published"
