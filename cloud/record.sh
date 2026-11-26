#!/bin/bash
# record.sh <job> <make outcome>: built or failed, committed to the data repo main branch.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || exit 1
cd "$GITHUB_WORKSPACE/data"; git checkout -q main 2>/dev/null || git checkout -q -B main origin/main; git fetch -q origin main; git reset -q --hard origin/main
J="jobs/$1"; R=""; [ -f "$RUNNER_TEMP/fail.txt" ] && R=$(cat "$RUNNER_TEMP/fail.txt")
if [ "$2" = "success" ]; then python "$GITHUB_WORKSPACE/cloud/state.py" . "$1" built; else python "$GITHUB_WORKSPACE/cloud/state.py" . "$1" failed "${R:-build failed, see the run}"; fi
cd "$GITHUB_WORKSPACE" && bash cloud/commit.sh "stage $1"
