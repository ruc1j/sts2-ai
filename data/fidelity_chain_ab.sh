#!/bin/zsh
# Cumulative panel for the fidelity chain (Rampart, Axebot respawn, ThievingHopper steal, enemy
# PlatingPower, Decimillipede move bodies, player debuff tick).
#
# Each of those fixes was measured on its own before it was committed.  This panel asks the question the
# objective actually cares about: taken together, do they move a run that has never cleared Act 3?
#
# arm = main HEAD.  control = the commit the chain starts after (d67896f), in its own worktree, so the
# two trees differ by exactly the chain.  Seeds are fresh: none of them appears in the earlier
# Rampart / Axebot / Plating / debuff panels, so seed choice cannot favour the arm.
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
seeds=(T5R8K2N9QP GYIJSAA6W7 Q6N3V8K2MT)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh chain_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh chain_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py chain_arm_b1 chain_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "CHAIN AB DONE"
