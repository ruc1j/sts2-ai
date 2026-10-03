#!/bin/zsh
# A/B for the enemy-side PlatingPower grant (commit ca5bd71).
#
# arm = main checkout HEAD, control = .wt-ctrl-119cb28 (its parent), so the trees differ by that commit
# only: FrogKnight / SlumberingBeetle start a fight with Block = PlatingAmount and re-grant it every
# turn while their plate thins by 1 per round.
#
# Seeds are the three with the most changed decisions under the same-record replay
# (data/attribution_rampart.py MONSTER.FROG_KNIGHT): H2LV6ZJ4XW 194, X3C9N6P4WQ 60, R4A8D2K7ME 46.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-119cb28
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
seeds=(H2LV6ZJ4XW X3C9N6P4WQ R4A8D2K7ME)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh plating_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh plating_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py plating_arm_b1 plating_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "PLATING AB DONE"
