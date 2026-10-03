#!/bin/zsh
# A/B for the player-debuff tick fix (commit 7ec2a06).
#
# Weak/Vulnerable/Frail tick at the end of the enemy side's turn, but a stack applied during that turn
# is exempt.  main ticked the fresh stack in the same transition (player read the debuff one turn late)
# and never ticked Frail at all.  Control is the parent commit's worktree, so the trees differ by that
# commit only.
#
# Seeds are the three with the most records where the player carries one of the three debuffs
# (B3N8V5T1WQ 153, SOS6XYXCNO 129, D6A1F8C3E5 127 out of 15,343 such records over 552 traces).
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-0aa9a71
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
seeds=(B3N8V5T1WQ SOS6XYXCNO D6A1F8C3E5)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh debuff_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh debuff_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py debuff_arm_b1 debuff_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "DEBUFF AB DONE"
