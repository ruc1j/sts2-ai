"""Decide whether a run's artifacts can be used as evidence.

A sweep line like `wins=0 losses=0 combat_records=44` is not itself evidence of a 0-win run: the game's
built-in AutoSlay can hang after a rewards screen, in which case the trace stops at a decision and the
mod log stops advancing.  Those runs are stalls, not losses, and must be excluded from arm-vs-control
comparisons.  This reads the last trace record and the mod log's last line and says which case it is.

Usage:
  python3 data/run_usability.py data/<tag>_<seed>_agent.jsonl data/<tag>_<seed>_mod.log
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

DECISION_PHASES = ('map', 'combat', 'shop', 'rest', 'event', 'card_reward')


def last_trace_record(path: Path) -> dict | None:
    last = None
    with path.open('r', encoding='utf-8-sig', errors='replace') as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except ValueError:
                    continue
    return last


def verdict(trace: Path, modlog: Path | None) -> tuple[str, str]:
    if not trace.exists() or trace.stat().st_size == 0:
        return 'unusable', 'trace が無い/空（run が combat に到達していない可能性が高い）'
    last = last_trace_record(trace)
    if last is None:
        return 'unusable', 'trace が読めない'
    phase = last.get('phase')
    if phase == 'combat_end':
        # The combat_end record carries `hp` and `won` at the top level, not inside a `player` block.
        hp = last.get('hp') if last.get('hp') is not None else (last.get('player') or {}).get('hp')
        won = last.get('won')
        if won is False and hp == 0:
            return 'usable', f'combat_end won=False hp=0 → 最期の戦闘で死んだ（結果として使える）'
        return 'usable', f'combat_end won={won} hp={hp} → 戦闘終了で終わっている'
    if phase in DECISION_PHASES:
        reason = f'最後の record が {phase} の決定 ✓ combat_end が無い'
        if modlog is not None and modlog.exists():
            age_min = (time.time() - modlog.stat().st_mtime) / 60.0
            tail = modlog.read_text(encoding='utf-8-sig', errors='replace').splitlines()[-1:] or ['']
            reason += f' ✓ mod log の最終行: {tail[0][:80]} ✓ 更新停止 {age_min:.0f} 分'
            if age_min >= 5.0:
                return 'unusable', reason + ' → game 内蔵 AutoSlay の stall（判定の母数から外す）'
        return 'check', reason + ' → log の更新が生きているか確認する'
    return 'check', f'最後の record の phase が想定外: {phase}'


def main(argv: list[str]) -> int:
    traces = [Path(arg) for arg in argv[1:]]
    for trace in traces:
        modlog = trace.with_name(trace.name.replace('_agent.jsonl', '_mod.log'))
        status, reason = verdict(trace, modlog)
        seed = trace.name[:-len('_agent.jsonl')].rsplit('_', 1)[-1]
        mark = {'usable': '✓ 使える', 'unusable': '✗ 使えない', 'check': '? 要確認'}[status]
        print(f'{trace.name}  seed {seed}: {mark} — {reason}')
        if status == 'unusable':
            print('   再実行: REPO=<tree> /Users/mao/.sts2/scripts/sweep3.sh <tag>_r ' + seed)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
