# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Platform split

This repo was authored on Windows, but the full pipeline also runs on macOS when the game is
installed via Steam there — PowerShell 7 (`pwsh`) itself is cross-platform, and so is the `dotnet`
SDK/tool the build depends on. There is nothing Windows-specific left except path conventions.

On macOS: the Steam install lives at `~/Library/Application Support/Steam/steamapps/common/Slay the
Spire 2`, with the game binary at `SlayTheSpire2.app/Contents/MacOS/SlayTheSpire2` and the native
libs (`sts2.dll` included — it's a managed .NET assembly, not an unmanaged Windows DLL, so it loads
fine under macOS `dotnet`) at `SlayTheSpire2.app/Contents/Resources/data_sts2_macos_arm64/`. Pass
`-GameDir` pointing there to every script below. `pwsh` may not be on `PATH` in a fresh shell even
when installed — check `which pwsh` first; if empty, it's commonly at
`/usr/local/microsoft/powershell/7-preview/pwsh`, and background launches especially need the full
path since `nohup pwsh ...` fails silently with `pwsh: No such file or directory` when relying on a
`PATH` the backgrounded process doesn't inherit. `decompile_game.ps1`'s `ilspycmd` step also works
unmodified against the macOS build's own `sts2.dll` — decompiling is not Windows-only either.

The Python half — agent policy, combat simulator, map tooling, and the full test suite — is
pure stdlib and runs anywhere; run `python` on Windows, `python3` on macOS.

## Commands

Run from the repo root — tests open `data/...` by relative path.

```bash
python3 -m unittest discover -p 'test_*.py'          # full suite (~1.5s)
python3 -m unittest test_combat.CombatTest.test_x    # single test
python3 -m unittest test_official_agent              # one module
```

Manual simulator inspection:

```bash
python3 combat.py data/enemies_overgrowth.json ENCOUNTER.SLIMES_WEAK --simulations 500 --seed 0
python3 ironclad.py --enemy-hp 40 --enemy-attack 8 --simulations 500 --seed 0
python3 act_map.py data/map_FV2EVHXLCW_overgrowth.json --show-path
```

Needs PowerShell 7 + the real game install (Windows path shown; see Platform split above for macOS
paths):

```powershell
pwsh -File .\build_official_mod.ps1 -GameDir '<game dir>'     # -> official_mod\bin\Release\net9.0\Sts2Ai.dll
# -AgentScript is required or the game's own built-in AutoSlay AI plays instead of ours; without
# -AgentMaxCombats only the FIRST combat of the run uses our agent (CombatBridge.cs silently falls
# back to the built-in AI after); without -StopAfterAct 3 the run stops right after Act 1 clears
# (default 1) even though it looks like it's still going - none of these three fail loudly if
# omitted, they just quietly change what actually ran.
pwsh -File .\run_official_autoslay.ps1 -GameDir '<game dir>' -AgentScript official_agent.py `
    -AgentMaxCombats 999 -StopAfterAct 3 -TimeoutSeconds 1800   # -Seed pins a run; refuses if game already running
pwsh -File .\export_enemies.ps1 -Act Overgrowth -Output .\data\enemies_overgrowth.json
pwsh -File .\decompile_game.ps1                                # then: python .\extract_effects.py ...
pwsh -NoProfile -File .\data\run_sim19.ps1                     # canned validation run (see below)
```

`build_official_mod.ps1` expects a dotnet SDK at `%TEMP%\sts2-ai-dotnet\dotnet.exe` (`$TMPDIR` on
macOS; override with `-Dotnet`). `run_official_autoslay.ps1` installs the mod into
`<game>\mods\Sts2Ai`, runs the game under an isolated `%TEMP%\sts2-ai-appdata-*` APPDATA, and cleans
both up in `finally` — if a run was killed by hand instead of letting the script finish, check for
and remove a stale `mods\Sts2Ai` folder before the next launch.

## Architecture

Two processes exchange JSON files; there is no socket, no RPC.

```
SlayTheSpire2.exe + official_mod/Sts2Ai.dll   <-- observation.json / action.json -->   official_agent.py
```

The C# side (`official_mod/*Bridge.cs`) swaps the game's phase Handlers only in agent mode, writes an
observation with a monotonic `seq` plus `legal_actions`, then polls for an action carrying the same
`seq`. Python polls at 25ms and writes via tmp-file + `os.replace`. Mismatched `seq` or partial JSON is
ignored on both sides; the C# wait deadline is 2 minutes, after which the phase takes a safe default
(usually skip). Phases: `map`, `combat`, `card_reward`, `rest`, `shop`, plus a hardcoded `event` bridge.

`official_agent.choose(observation, enemy_data, simulations)` is the single dispatch point — it routes
on `phase` to `choose_map` / `choose_card_reward` / `choose_shop` / `choose_rest`, and everything else
is combat. Combat tries, in order: Sandpit escape, Crab facing, potions, lethal attacks,
`rollout_choice`, Defend, card priority, `end_turn`. Lethal is checked before `rollout_choice` on
purpose — greedy rollout can pass up a guaranteed kill for a different move that scores well but
misses the kill, so a confirmed lethal short-circuits before rollout ever runs. Anything the
simulator can't model (`KeyError`, `ValueError`, `NotImplementedError`, `StopIteration`) falls
through to the heuristic tail — that fallback is load-bearing, keep it.

**Two independent simulators.** `combat.py` is the one wired into the live loop: multi-enemy,
frozen dataclasses (`Enemy`, `Combat`), `search()` runs greedy rollouts (not random) over each first
move. `ironclad.py` is a standalone single-enemy MCTS model used only from its own CLI and tests —
changes to one do not propagate to the other.

**Enemies are data, not code.** `data/enemies_*.json` holds per-monster state machines
(`initial_state`, `states[].intents`, `states[].effects`) exported from the game DLL by
`export_enemies.ps1` and enriched by `extract_effects.py` from decompiled C#. `combat.py` interprets
those commands (`DamageCmd.Attack`, `CardPileCmd.*`, …). Adding an enemy behaviour usually means
regenerating JSON and teaching `_enemy_turn` a command — not writing an enemy class.

## Working in this repo

- **Read `docs/CODEWIKI.md` before touching policy.** Nearly every threshold in `official_agent.py`
  (block-starvation 40%, Perfected Strike capped at 2, Shackling first vs. Fortifier only with block,
  fewest-combats map routing) is a recorded fix for a specific observed failure, with the run that
  caused it named. Changing a number without reading why it is that number re-opens a closed bug.
- `test_official_agent.py` (1400+ lines) is a policy regression suite, not unit tests. A tuning change
  that breaks 30 of them is usually the change being wrong, not the tests being stale.
- `test_official_result.py` and `test_official_trace.py` assert against committed artifacts pinned to
  seed `FV2EVHXLCW` and game `v0.107.1`. Regenerate those artifacts only alongside a real run.
- `.gitignore` drops `*_result.json`, `*_errors.log`, and most `data/map_*.json`; the pinned
  artifacts above are force-tracked exceptions. New validation runs land as `data/run_simN.ps1` with
  their outputs ignored.
- After a game update: rebuild the mod, re-export enemy/map JSON, run the Python suite, then a minimal
  official run, then check trace/result. The bridges bind to internal game APIs and will silently
  mis-observe rather than fail loudly.
- Docs are Japanese, code and comments are English. Keep that split. Commit messages are Japanese
  (user preference, overrides the code/comments convention above).
- After each verified fix (tests passing), commit it before moving to the next one — small commits
  per fix, not one giant batch at the end of a session.
- After every official run (`run_official_autoslay.ps1`), analyze the cause of the loss (or the
  run's outcome generally) before launching the next one — check the trace/log for a genuinely new
  monster mechanic or agent misplay, not just "known matchup, retry". Fix what you find, verify with
  a test, commit, then run again. Don't blind-retry without this step in between.
- As part of that analysis, check the trace for cards the deck picked up but never played a single
  time that run — a strong signal the card isn't modeled in `combat.py` (silently excluded from
  `legal_actions`, invisible to `search()`) rather than just a bad pick. Flame Barrier was found
  this way: rated highly for reward picks but entirely unplayable in combat.
- A death with no matching damage source in the trace (HP drops far more than any logged attack
  could deal, or `search_value` stayed confident right up to the loss) usually means a card or
  power's *side effect* is unmodeled, not that the scoring is wrong - the scoring only knows what
  `combat.py` tells it. Decompile the card/power in question (works on macOS too, see Platform
  split) before touching `search()`/`_step_score()` itself. `CARD.THE_GAMBIT` (50 block for 0
  cost, but the next unblocked hit while its power is active kills outright regardless of HP) and
  Wriggler's `Infection` status card (3 flat damage if still in hand at turn end, entirely
  separate from its `HasTurnEndInHandEffect` cousins Toxic/Burn already being handled) were both
  found this way — both looked like scoring bugs at first glance and were actually missing
  mechanics.
