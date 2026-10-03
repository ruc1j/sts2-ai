#!/bin/zsh
# Second Rampart panel: the three seeds whose decisions the grant moved but that the first panel
# (H2 / B3 / D6) did not cover, so the sign of that fix is not read off a single seed.
#
# arm = `cd24b1f` (Rampart in, Axebot and ThievingHopper fixes not yet in), control = `d67896f`
# (its parent).  Both trees therefore differ by commit `5f655ff` only, which keeps the divergence
# attributable to the Rampart grant even though main has moved on since.
set -u
repo=/Users/mao/workspace/sts2-ai
arm=$repo/.wt-ctrl-cd24b1f
ctrl=$repo/.wt-ctrl-d67896f
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
for tree in $arm $ctrl; do
  if [ ! -f "$tree/official_mod/bin/Release/net9.0/Sts2Ai.dll" ]; then
    print -- "refusing: $tree has no built Sts2Ai.dll"
    exit 1
  fi
done
seeds=(SOS6XYXCNO 9X9WQB4QIH R4A8D2K7ME)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh rampart_ctrl_b2 "${seeds[@]}"
REPO=$arm /Users/mao/.sts2/scripts/sweep2.sh rampart_arm_b2 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py rampart_arm_b2 rampart_ctrl_b2 "$arm" "$ctrl" "$seed"
done
print -- "RAMPART AB2 DONE"
