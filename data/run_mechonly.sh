#!/bin/zsh
# Mechanisms-only batch: the arm with the generation sets pinned to the control shapes, so a divergence
# against the control runs is mechanism-only. Refuses if the game is already running, if policy code
# differs from HEAD, or if a stale mod install is present.
set -u
repo=/Users/mao/workspace/sts2-ai
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
cd "$repo" || exit 1
if git status --short -- official_agent.py combat.py | grep -q .; then
  print -- "refusing: policy code differs from HEAD"
  exit 1
fi
game='/Users/mao/Library/Application Support/Steam/steamapps/common/Slay the Spire 2'
export PATH="/opt/homebrew/bin:$PATH"
userdata="$HOME/Library/Application Support/SlayTheSpire2"
snapshot="$HOME/.sts2/userdata-pin"
seeds=(H2LV6ZJ4XW AM8C6YXHSG R8V2H6N4ZB P3V8N5K2RX)
for seed in "${seeds[@]}"; do
  rsync -a --delete "$snapshot"/ "$userdata"/
  prefix="data/mechonly_${seed}"
  pwsh -File ./run_official_autoslay.ps1 \
    -GameDir "$game" -Seed "$seed" -TimeoutSeconds 1800 -StopAfterAct 3 \
    -AgentScript ./data/mechonly_agent.py -AgentMaxCombats 100 -AgentSimulations 100 \
    '-Visible:$false' -LogFile "./${prefix}_mod.log" \
    -ResultFile "./${prefix}_result.json" -AgentTrace "./${prefix}_agent.jsonl" \
    -AgentErrorLog "./${prefix}_agent.err" -MapFile "./${prefix}_map.json" \
    >"${prefix}_stdout.log" 2>&1
  code=$?
  wins=$(python3 -c "
import json,sys
w=l=0
for line in open(sys.argv[1], encoding='utf-8-sig'):
    try: e=json.loads(line)
    except ValueError: continue
    if e.get('phase')=='combat_end':
        w += e.get('won') is True; l += e.get('won') is False
print(w, l)" "${prefix}_agent.jsonl")
  print -- "RESULT mechonly ${seed} wins/losses ${wins} exit=${code}"
  rsync -a --delete "$snapshot"/ "$userdata"/
done
print -- "SWEEP DONE mechonly"
