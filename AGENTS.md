# Repository Guidelines

## Project Structure & Module Organization

Root-level Python modules contain the agent and simulators: `official_agent.py` dispatches phase decisions, `combat.py` provides the live rollout model, `ironclad.py` is a separate MCTS model, and `act_map.py` validates routes. Harmony bridge code lives in `official_mod/`; artifacts in `data/`; documentation in `docs/`; and tests in root-level `test_*.py` files.

## Architecture Overview

The C# mod and Python agent poll `observation.json` and `action.json`. Preserve `seq` validation, atomic replacement, timeouts, and legal fallbacks. Official runs use `combat.py`, not `ironclad.py`.

## Build, Test, and Development Commands

Run commands from the repository root:

```bash
python3 -m unittest discover -p 'test_*.py'
python3 combat.py data/enemies_overgrowth.json ENCOUNTER.SLIMES_WEAK --simulations 500 --seed 0
pwsh -File ./build_official_mod.ps1 -GameDir '<game directory>'
pwsh -File ./run_official_autoslay.ps1 -GameDir '<game directory>' -Seed FV2EVHXLCW
```

Use `python` instead of `python3` on Windows. Building requires .NET 9 and an installed copy of Slay the Spire 2. The Python suite uses only the standard library.

## Coding Style & Naming Conventions

Use four-space indentation. Python uses `snake_case`, `PascalCase` classes, uppercase constants, and type hints. C# members and PowerShell parameters use `PascalCase`. No formatter or linter is configured; match surrounding code. Write code and comments in English, documentation in Japanese.

## Testing Guidelines

Tests use `unittest`; name files `test_<module>.py` and methods `test_<behavior>`. Add the smallest regression test, run its module, then the full suite. Replace pinned artifacts only after a real run with the recorded seed and version.

## Commit & Pull Request Guidelines

Use short Japanese subjects such as `Ruptureをシミュレータに実装`, with one verified fix per commit. Pull requests must describe behavior, the change, and test results. Game-facing changes also require the game version, seed, and relevant log or trace excerpts.

## Run Safety

Official runs write to tracked default artifact paths. Use explicit `-ResultFile`, `-AgentTrace`, `-MapFile`, and `-LogFile` paths for experiments, and never launch concurrent runs against the same files.
