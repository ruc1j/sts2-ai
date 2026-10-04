#!/bin/zsh
# Retry of batch 2's arm leg.  The first attempt was killed mid-run (exit=143), which left a stale
# <game>/SlayTheSpire2.app/Contents/MacOS/mods/Sts2Ai behind, and the two following runs refused to start
# with "refusing to overwrite existing mod" (wins=0 losses=0 exit=1).  The stale folder was removed by
# hand after checking it held only Sts2Ai.dll/Sts2Ai.json.  The control leg (15 / 14 / 6 wins) is valid.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-pot2
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
seeds=(P3V8N5K2RX F9P4X7N2LC R9TB3LKD6M)
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh gate_arm_b2r "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py gate_arm_b2r gate_ctrl_b2 "$repo" "$ctrl" "$seed"
done
print -- "GATE AB2 ARM RETRY DONE"
