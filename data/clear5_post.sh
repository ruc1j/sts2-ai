#!/bin/zsh
# Per-run step for run_clear5.sh: copy artifacts to the main checkout, write and commit the manifest,
# print a one-line outcome, and apply the preregistered stop (first 68 runs with zero Act 3 clears).
# usage: SOURCE_COMMIT=<sha> ARM=<arm> SEEDS_FILE=<file> clear5_post.sh <tag> <seed> <candidate_repo>
set -u
tag=$1; seed=$2; cand=$3
main=/Users/mao/workspace/sts2-ai
cd "$main" || exit 1
if [[ "$cand" != "$main" ]]; then rsync -a "$cand"/data/"${tag}_${seed}"_* data/; fi
python3 .dsh/make_manifest.py "$tag" "$seed" --panel "$tag" --arm "$ARM" --seeds-file "$SEEDS_FILE" \
  --source-commit "$SOURCE_COMMIT" --runner data/run_clear5.sh \
  --dll "$cand/official_mod/bin/Release/net9.0/Sts2Ai.dll" >/dev/null 2>&1 || print -- "POST manifest failed ${seed}"
git add "data/${tag}_${seed}_manifest.json"
git commit -q -m "$(print -- "${tag}のmanifestを追加（${seed}）\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")" -- "data/${tag}_${seed}_manifest.json" || print -- "POST commit failed ${seed}"
python3 data/clear5_summary.py "$tag" "$seed" "$SEEDS_FILE"
