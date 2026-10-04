#!/bin/zsh
# A/B panel for the Crimson Mantle self-damage fix (commit ad3fa1a).
#
# arm = main HEAD.  control = .wt-ctrl-mantle at b46e5d9, so the two trees differ by that one commit
# (docs-only commits are not involved).  Same mod binary, checked by md5.
#
# What the fix changes: the rollout used to skip the 1 Unblockable self-damage that CrimsonMantlePower
# deals at the player's turn start, because the game keeps that number in a DynamicVar and exports only
# the mantle counter.  A state rebuilt from an observation had no marker, so every mantle turn was 1 HP
# optimistic.  Offline replay: 0/1907 matching end-turn replays -> 1898/1907, and 563 decisions changed
# across 12 seeds.  This panel is the run-level outcome of that pessimism.
#
# Seeds are three fresh seeds whose recorded runs held CrimsonMantlePower the most (804 / 218 / 52
# observations) and played the card.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-mantle
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
seeds=(Z6MK8PGN4S K71SQ5B0Q2 EH8UMY96NC)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh mantle_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh mantle_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py mantle_arm_b1 mantle_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "MANTLE AB DONE"
