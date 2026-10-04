#!/bin/zsh
# A/B panel for the potion rollout gate expansion (the commit after cc04e3d): the simulator gained
# PotionOfBinding, CureAll, Clarity and RadiantTincture, and this change lets the rollout price those
# four.  Shackling and LuckyTonic are deliberately left out - Shackling's -7 Strength lasts one enemy
# turn only and a recorded fix reserves it for boss-length fights.
#
# arm = main HEAD.  control = .wt-ctrl-pot2 at 3690e55, i.e. before both the simulator modelling (cc04e3d)
# and the gate entry (e0c416d), so the arms differ by those two commits together.  Same mod binary,
# checked by md5.
#
# Batch 2: the next three fresh seeds by recorded plays of the four potions (13 / 8 / 8 plays), used to
# resolve the -1 that batch 1 showed (13-13, 14-14, 13-12).
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-pot2
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
if [ ! -f $ctrl/official_mod/bin/Release/net9.0/Sts2Ai.dll ]; then
  print -- "refusing: the control worktree has no mod binary"
  exit 1
fi
if [ "$(md5 -q $repo/official_mod/bin/Release/net9.0/Sts2Ai.dll)" != "$(md5 -q $ctrl/official_mod/bin/Release/net9.0/Sts2Ai.dll)" ]; then
  print -- "refusing: arm and control would run different mod binaries"
  exit 1
fi
seeds=(P3V8N5K2RX F9P4X7N2LC R9TB3LKD6M)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh gate_ctrl_b2 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh gate_arm_b2 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py gate_arm_b2 gate_ctrl_b2 "$repo" "$ctrl" "$seed"
done
print -- "GATE AB2 DONE"
