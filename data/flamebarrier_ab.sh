#!/bin/zsh
# A/B panel for the per-hit Flame Barrier reflection (commit f1a9a10).
#
# arm = main HEAD.  control = .wt-ctrl-fb at 7f276af, so the policy code differs by that one commit.
# Same mod binary, checked by md5.
#
# What the fix changes: FlameBarrierPower.AfterDamageReceived reflects its amount back at the attacker
# on every damage instance, so a 3-hit attack reflects three times.  The model reflected once per attack.
# Offline replay of 404 recorded single-enemy end-turn cases with FlameBarrierPower: enemy-HP agreement
# 245/404 -> 371/404, and 59 recorded decisions changed across 15 seeds.
#
# Seeds are three fresh seeds whose recorded runs held FlameBarrierPower the most (46 / 33 / 28
# observations) and actually played the card.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-fb
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
seeds=(C7N4V9P2RX V7K2T9M5RH S4QFLNDMB3)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh fb_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh fb_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py fb_arm_b1 fb_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "FLAMEBARRIER AB DONE"
