#!/bin/bash
# save.sh <job>: pushes the result folder back to the private repo, on its own branch so main stays small.
set -euo pipefail
[[ "$1" =~ ^[a-z0-9-]+$ ]] || exit 1
cd data; [ -d "jobs/$1/result" ] || { echo "nothing to save"; exit 0; }
[ -f "jobs/$1/result/status.txt" ] || echo FAIL > "jobs/$1/result/status.txt"
git config user.name billio-bot; git config user.email billio-bot@users.noreply.github.com
git checkout -q --orphan "out-$1"; git rm -rq --cached . ; git add -f "jobs/$1/result"; git commit -q -m "result $1"; git push -q -f origin "out-$1" && echo "saved"
