#!/bin/zsh
# A/B panel for the hybrid play counters (commit f2a107c), measured against the pile-only version.
#
# arm = main HEAD.  control = .wt-ctrl-pile at 86ffe4c, so the policy code differs by exactly f2a107c.
# Same mod binary, checked by md5.
#
# What the fix changes: counting every card that left the hand counted cards that an effect discarded or
# exhausted (Burning Pact and Fiend Fire exhaust other cards, Dark Embrace discards them) as plays, which
# inflated the turn's Skill count and made the model deal 5 the game never dealt in 36 recorded plays.  Own
# plays are now taken from the actions the agent chose, and an unexplained departure counts as a play only
# when the card was never seen in hand this turn (which is what an autoplay looks like).  Offline replay:
# agreement 97.54% -> 97.65% (the previous commit's 97.36% baseline is .wt-ctrl-plays at 2426496), combo
# relic mismatches 2,507 -> 2,401, LETTER_OPENER over-damage 36 -> 0 and its under-damage 55 -> 13.
#
# Seeds: the same three that measured the previous commit (E3L7S9A4KU, Q2W7N4K9DX, V7D3M9H2XW - the corpus
# seeds with the most combo-relic observations that no earlier panel had measured).
#
# NOT RUN.  After this script was written, attribution against the pile-only control replayed 13,325
# LETTER_OPENER records and found 0 changed decisions across 0 seeds: the corrected counting changes the
# damage the model reports but not the action the agent picks on any recorded state, so a win-rate panel
# had nothing it could move.  The script is kept so the comparison can be re-run if a later change makes
# those decisions live again.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-pile
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
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh plays2_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh plays2_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py plays2_arm_b1 plays2_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "PLAYS2 AB DONE"
