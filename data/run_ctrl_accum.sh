#!/bin/zsh
# Accumulates control runs (current main) on fresh seeds until a deadline, one game at a time.
# usage: run_ctrl_accum.sh <deadline_epoch> <seeds_file> <tag>
# Stops (without retrying) on any anomaly: running game, stale mod install, dirty policy code,
# non-zero wrapper exit, or a missing trace. Leaves artifacts for the manifest step.
set -u
repo=/Users/mao/workspace/sts2-ai
deadline=$1; seeds_file=$2; tag=$3
game='/Users/mao/Library/Application Support/Steam/steamapps/common/Slay the Spire 2'
export PATH="/opt/homebrew/bin:$PATH"
userdata="$HOME/Library/Application Support/SlayTheSpire2"
snapshot="$HOME/.sts2/userdata-pin"
cd "$repo" || exit 1
for seed in ${(f)"$(<$seeds_file)"}; do
  if (( $(date +%s) + 900 > deadline )); then print -- "DEADLINE reached before ${seed}"; break; fi
  if pgrep -f '^/.*/Contents/MacOS/Slay the Spire 2' > /dev/null; then print -- "ANOMALY game already running"; exit 1; fi
  if [[ -e "$game/SlayTheSpire2.app/Contents/MacOS/mods/Sts2Ai" ]]; then print -- "ANOMALY stale mods/Sts2Ai"; exit 1; fi
  if git status --short -- official_agent.py combat.py official_mod | grep -q .; then print -- "ANOMALY policy code differs from HEAD"; exit 1; fi
  [[ -e "data/${tag}_${seed}_agent.jsonl" ]] && continue
  rsync -a --delete "$snapshot"/ "$userdata"/
  prefix="data/${tag}_${seed}"
  start=$(date +%s)
  pwsh -File ./run_official_autoslay.ps1 \
    -GameDir "$game" -Seed "$seed" -TimeoutSeconds 1800 -StopAfterAct 3 \
    -AgentScript official_agent.py -AgentMaxCombats 100 -AgentSimulations 100 \
    '-Visible:$false' -LogFile "./${prefix}_mod.log" \
    -ResultFile "./${prefix}_result.json" -AgentTrace "./${prefix}_agent.jsonl" \
    -AgentErrorLog "./${prefix}_agent.err" -MapFile "./${prefix}_map.json" \
    >"${prefix}_stdout.log" 2>&1
  code=$?
  end=$(date +%s)
  rsync -a --delete "$snapshot"/ "$userdata"/
  print -- "{\"seed\":\"${seed}\",\"exit\":${code},\"started\":${start},\"finished\":${end}}" > "${prefix}_runmeta.json"
  usab=$(python3 data/run_usability.py "${prefix}_agent.jsonl" "${prefix}_mod.log" 2>&1 | head -1)
  print -- "RESULT ${seed} exit=${code} secs=$((end-start)) ${usab}"
  # Exit 1 is the game's normal exit after a death (run_official_autoslay.ps1 rethrows it), so only a
  # timeout, a missing trace, or an unusable trace counts as an anomaly.
  if grep -q "timed out after" "${prefix}_stdout.log" || [[ ! -s "${prefix}_agent.jsonl" ]] || [[ "$usab" == *"✗"* ]]; then print -- "ANOMALY timeout/missing/unusable trace for ${seed}"; exit 1; fi
done
print -- "ACCUM DONE ${tag}"
