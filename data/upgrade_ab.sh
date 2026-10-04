#!/bin/zsh
# A/B panel for the card upgrade-value fix (commit a94a4dc: 18 cards' CARD_UPGRADE_DAMAGE /
# ALL_ENEMY_UPGRADE_DAMAGE taken from each card's own DynamicVars.Damage.UpgradeValueBy).
#
# arm = main HEAD.  control = bef34e7, the commit immediately before the fix, in its own worktree, so
# the two trees differ by exactly that change.  Offline replay already showed the fix moves 158
# decisions across 17 seeds; this panel is the run-level outcome measure, which replay cannot provide.
#
# Seeds are the three fresh seeds whose recorded runs had the most replayed decision changes
# (M5W9C3T7LQ 10 listed, D1W9Y3B7FC 5, C9RH5TXB3L 5) and none of them appears in the earlier
# Rampart / Axebot / Plating / debuff / fidelity-chain panels.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-bef34e7
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
seeds=(M5W9C3T7LQ D1W9Y3B7FC C9RH5TXB3L)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh upgrade_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh upgrade_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py upgrade_arm_b1 upgrade_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "UPGRADE AB DONE"
