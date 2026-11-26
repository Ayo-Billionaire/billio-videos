#!/bin/bash
# record.sh <job> <make outcome>: built or failed, committed to the data repo main branch.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || exit 1
# save.sh leaves the folder on an orphan result branch with every file untracked: force back to main.
cd "$GITHUB_WORKSPACE/data"; git fetch -q origin main; git checkout -q -f -B main origin/main; git reset -q --hard origin/main; git clean -qfd jobs/*/result 2>/dev/null || true
J="jobs/$1"; R=""; [ -f "$RUNNER_TEMP/fail.txt" ] && R=$(cat "$RUNNER_TEMP/fail.txt")
if [ "$2" = "success" ]; then python "$GITHUB_WORKSPACE/cloud/state.py" . "$1" built; else python "$GITHUB_WORKSPACE/cloud/state.py" . "$1" failed "${R:-build failed, see the run}"; fi
cd "$GITHUB_WORKSPACE" && bash cloud/commit.sh "stage $1"
