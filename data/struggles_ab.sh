#!/bin/zsh
# A/B panel for the Mr Struggles fix (commit b94c901: the relic deals the new turn number in damage to
# every enemy at the start of each player turn, which the rollout could not see at all).
#
# arm = main HEAD.  control = e4b14b0 (the commit right before the fix) in .wt-ctrl-mr, so the two trees
# differ by that change only, and both run the same mod binary (checked by md5 before launching).
# Offline replay already moved the turn-boundary agreement in relic runs from 53.7% to 79.4% and changed
# 506 recorded decisions across 8 seeds; this panel is the run-level outcome measure.
#
# Seeds are three fresh seeds whose recorded runs hold RELIC.MR_STRUGGLES *and* reached an Act 3 boss, so
# the relic's damage actually had a long fight to accumulate in (unlike the stun panel, where the
# mechanic appeared in about one fight per run).
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-mr
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
seeds=(VTW80ZJA2G R8V2H6N4ZB X7M4Q9B2KT)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh struggles_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh struggles_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py struggles_arm_b1 struggles_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "STRUGGLES AB DONE"
