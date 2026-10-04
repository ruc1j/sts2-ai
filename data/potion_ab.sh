#!/bin/zsh
# A/B panel for the potion fix (commit 257c4fe: the simulator gained Speed/Flex/Swift/Regen/Fortifier/
# Weak/Vulnerable potions, and ROLLOUT_POTION_IDS now lets the agent price them).
#
# arm = main HEAD.  control = .wt-ctrl-potion at 7f583c3.  Between them only 257c4fe changes agent
# behaviour; 3aee364 (measurement tooling) and 587cb46 (documentation) do not touch the agent.  Both
# trees run the same mod binary, checked by md5 before launching.
#
# Offline replay says the change is load-bearing: 0 of 758 recorded potion plays of those seven potions
# were simulatable before, 655 are now, and all 655 reproduce the game's player HP.  This panel is the
# run-level outcome measure, because widening the set of potions the agent can consider changes behaviour.
#
# Seeds are three fresh seeds whose recorded runs played those potions the most (92 / 80 / 51 plays) and
# reached an Act 3 boss.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-potion
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
seeds=(AM8C6YXHSG M5PC8TQ3BN NFH3RMVJ6D)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh potion_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh potion_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py potion_arm_b1 potion_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "POTION AB DONE"
