#!/bin/zsh
# Third batch: seeds where Chains is present in the observed state (the gate has the largest decision
# reach after Fiddle). Control must be re-taken at `e808bdf`; the arm stage uses the pinned harness so the
# generation-set difference cannot confound the attribution. Never two game instances at once.
set -u
repo=/Users/mao/workspace/sts2-ai
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
cd "$repo" || exit 1
if git status --short -- official_agent.py combat.py | grep -q .; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
seeds=(D6A1F8C3E5 X3C9N6P4WQ SOS6XYXCNO L3PN5HBQ8T B4J8Q1R6YK T5R8K2N9QP)
REPO=$repo/.wt-ctrl-e808bdf /Users/mao/.sts2/scripts/sweep2.sh mechonly_ctrl_b3 "${seeds[@]}"
AGENT=./data/mechonly_agent.py REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh mechonly_arm_b3 "${seeds[@]}"
