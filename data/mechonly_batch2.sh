#!/bin/zsh
# Second mechanisms-only batch, for seeds where the corpus shows a mechanism in the observed state.
# Control must be re-taken at the same commit as the first batch (`e808bdf`) because the existing
# control-era runs for these seeds are at other commits and are not comparable.
# Run this only after the current batch has finished (never two game instances at once).
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
seeds=(U2M7K5F9RA T3XQ7WM2VP M7C4Q9V2RH C8Q1Z7E3KS M5W9C3T7LQ V7D3M9H2XW)
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh mechonly_ctrl_b2 "${seeds[@]}"
# The arm stage must use the pinned harness, otherwise the generation-set difference confounds the
# attribution again. sweep2.sh takes the agent script through AGENT.
AGENT=./data/mechonly_agent.py REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh mechonly_arm_b2 "${seeds[@]}"
