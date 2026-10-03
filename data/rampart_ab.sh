#!/bin/zsh
# A/B for the RampartPower grant (commit 5f655ff).
#
# The two trees differ by exactly that commit (combat.py grant + POWER_NAMES mapping), so a run-level
# divergence is attributable to the grant alone.  No generation-set pinning is needed: both trees carry
# the same STOKE_GENERATION / INFERNAL_BLADE_ATTACKS, so the card table cannot confound the comparison.
#
# Seeds are the three that showed the most changed decisions under the same-record replay
# (data/attribution_rampart.py): H2LV6ZJ4XW 25, B3N8V5T1WQ 10, D6A1F8C3E5 3.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-d67896f
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
seeds=(H2LV6ZJ4XW B3N8V5T1WQ D6A1F8C3E5)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh rampart_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh rampart_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py rampart_arm_b1 rampart_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "RAMPART AB DONE"
