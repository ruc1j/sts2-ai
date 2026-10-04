#!/bin/zsh
# A/B panel for the STUNNED fix (commit fc54807: the runtime stun state is now modeled, so a stunned
# monster no longer performs its move on the turn the game gives it nothing).
#
# arm = main HEAD.  control = ba30482 (the commit right before the fix) in its own worktree, so the two
# trees differ by exactly that change, and both use the same freshly rebuilt Sts2Ai.dll.  Offline
# replay already showed the fix moves 241 decisions in Bowlbug Rock fights across 45 seeds and 52
# decisions in Tunneler fights across 21 seeds; this panel is the run-level outcome measure.
#
# Seeds are three fresh seeds (none used in an earlier panel) whose recorded runs had the most replayed
# decision changes under the stun filter: L3PN5HBQ8T 10, F6L1X4P8MS 6, P7M4C2W9KS 5.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-ba30482
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
seeds=(L3PN5HBQ8T F6L1X4P8MS P7M4C2W9KS)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh stun_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh stun_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py stun_arm_b1 stun_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "STUN AB DONE"
