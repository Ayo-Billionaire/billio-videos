#!/bin/bash
# commit.sh <message>: commit small state files of the data repo (never videos) and push, retrying on a race.
set -uo pipefail
cd "$GITHUB_WORKSPACE/data"; git config user.name billio-bot; git config user.email billio-bot@users.noreply.github.com
shopt -s nullglob   # a pattern with no match must not sink the whole add (it did: "pathspec did not match", nothing saved)
F=(jobs/*/state.json jobs/*/review*.json jobs/*/published.json jobs/*/art.json jobs/*/picks.json jobs/*/plan.final.json writer/published.json writer/used-episodes.json pool/catalog.json alerts.json)
E=(); for f in "${F[@]}"; do [ -e "$f" ] && E+=("$f"); done
[ ${#E[@]} -gt 0 ] && git add -A -- "${E[@]}"
git add -u -- jobs   # also save removals and edits of files already in the repo (a retired review.json)
git diff --cached --quiet && { echo "nothing to commit"; exit 0; }
git commit -q -m "$1"
for i in 1 2 3 4; do git pull -q --rebase origin main && git push -q origin HEAD:main && { echo "pushed"; exit 0; }; sleep $((i * 5)); done
echo "push failed"; exit 1
