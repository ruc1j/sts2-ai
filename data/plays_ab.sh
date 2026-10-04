#!/bin/zsh
# A/B panel for the play-counter reconstruction (commits 4c89254 + e7d8836).
#
# arm = main HEAD.  control = .wt-ctrl-plays at 2426496, i.e. the same tree without those two commits.
# The two commits are one mechanism - make the turn's play counts visible, then apply the combo bonus at
# the game's timing - so they are measured together, and that is stated here rather than pretending the
# control is a single commit back.  Same mod binary, checked by md5.
#
# What the change does: the bridge exports relic ids only, so every state rebuilt from an observation
# started with zero cards played, and the rules that fire on the 3rd Skill (LetterOpener, 5 unpowered
# damage), the 3rd Attack (Kusarigama 6, Shuriken Strength, Ornamental Fan block) and the 10th attack
# (Pen Nib doubling) could never be priced mid-turn.  The counters now come from the discard and exhaust
# piles, which also counts the cards the game played by itself.  Offline replay over 101,464 recorded
# plays: agreement 97.36% -> 97.54%, and the LetterOpener family's over-damage-by-the-game cases fell
# from 393 to 93.
#
# Seeds: the three corpus seeds with the most combo-relic combat observations that no earlier panel has
# measured (289 / 270 / 255 observations, of which 199 / 196 / 174 are mid-turn states where the counters
# matter).  None of them had been used in an arm-control panel before.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-plays
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
seeds=(E3L7S9A4KU Q2W7N4K9DX V7D3M9H2XW)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh plays_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh plays_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py plays_arm_b1 plays_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "PLAYS AB DONE"
