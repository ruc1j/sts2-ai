#!/bin/zsh
# A/B for the Axebot StockPower respawn (commit 03b2055).
#
# The two trees differ by exactly that commit (initial_combat grant, _mark_enemy_death respawn, the
# per-copy StockAmount read, and the POWER_NAMES mapping), so a run-level divergence is attributable
# to the respawn alone.  No generation-set pinning is needed: both trees carry the same
# STOKE_GENERATION / INFERNAL_BLADE_ATTACKS.
#
# Seeds are the four whose recorded decisions the fix moved (data/attribution_rampart.py
# POWER.STOCK_POWER): B3N8V5T1WQ 67, D6A1F8C3E5 33, R4A8D2K7ME 26.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-cd24b1f
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
seeds=(B3N8V5T1WQ D6A1F8C3E5 R4A8D2K7ME)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh axebot_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh axebot_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py axebot_arm_b1 axebot_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "AXEBOT AB DONE"
