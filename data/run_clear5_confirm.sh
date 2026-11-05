#!/bin/zsh
# Confirmation panel: each unseen seed runs on the control, then the candidate, one game at a time.
# usage: run_clear5_confirm.sh <deadline_epoch> <candidate_repo> <candidate_commit> <control_commit> [seeds_file]
# Stops on the first runner anomaly; rerun with the same arguments to continue (finished runs are skipped).
set -u
deadline=$1; cand=$2; cand_commit=$3; ctrl_commit=$4
main=/Users/mao/workspace/sts2-ai
seeds_file=${5:-$main/data/act3clear5_confirm_seeds.txt}
one=$(mktemp -t clear5_confirm)
trap 'rm -f "$one"' EXIT
export POST_RUN=$main/data/clear5_post.sh SEEDS_FILE=data/act3clear5_confirm_seeds.txt NO_GATE=1
cd "$main" || exit 1
for seed in ${(f)"$(<$seeds_file)"}; do
  print -- "$seed" > "$one"
  REPO=$main SOURCE_COMMIT=$ctrl_commit ARM=control /bin/zsh data/run_clear5.sh "$deadline" "$one" astra_clear5_confirm_ctrl || exit 1
  REPO=$cand SOURCE_COMMIT=$cand_commit ARM=candidate /bin/zsh data/run_clear5.sh "$deadline" "$one" astra_clear5_confirm_c2 || exit 1
done
print -- "CONFIRM DONE"
