#!/bin/zsh
# A/B panel for the burrowed block retention fix (commit 6bf743a).
#
# arm = main HEAD.  control = .wt-ctrl-burrow at 01e3ce2, so the policy code differs by that one commit.
# Same mod binary, checked by md5.
#
# What the fix changes: Hook.ShouldClearBlock consults every ShouldClearBlock override, and BurrowedPower
# answers false for its owner, so a burrowed Tunneler keeps the block the player left it with.  The model
# wiped enemy block at every enemy-turn boundary.  Offline replay of 186 recorded burrowed end-turn cases:
# enemy block agreement 8/186 -> 184/186, enemy HP agreement 163/186 -> 181/186.
#
# Seeds: this mechanism only fires against MONSTER.TUNNELER (1,338 observations in the corpus), and the
# seeds with the most TUNNELER observations (640 / 363 / 355) are all seeds already measured in earlier
# panels.  A fresh seed would most likely never meet a Tunneler and produce a no-op panel, so this panel
# deliberately re-measures known-Tunneler seeds and is labelled as mechanism-targeted rather than a new
# seed sample.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-burrow
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
seeds=(H2LV6ZJ4XW P3V8N5K2RX L3PN5HBQ8T)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh burrow_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh burrow_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py burrow_arm_b1 burrow_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "BURROW AB DONE"
