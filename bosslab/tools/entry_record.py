#!/usr/bin/env python3
"""Python-side mirror + integrity check of the BossLab entry write-back record (the 20892cd C# hook).

The C# hook `RestoreRecordedEntryState` (commit 20892cd, default off) reads, from each plan trial, a recorded
combat-start to replay: enemy `id/hp/max_hp` plus the four card piles (`draw_pile`/`hand`/`discard_pile`/
`exhaust_pile`, each
a list of `{id, upgrade, enchantment}`), so a fixed-entry boss fight reproduces the exact entry state (the
double-fired relic HP for FORGOTTEN_SOUL / BLESSED_ANTLER that fid5 found mismatched). The C# is not built
here, so this module only builds the record from a captured first-combat observation and checks that the
record is internally consistent and faithfully reproduces that observation — the Python-side guarantee that
what we hand the hook is well-formed. The hook stays default off unless a plan or env turns it on.

Usage (library): `build_entry_record(obs)` then `entry_record_problems(rec)`.
"""
import os

PILE_TYPES = ("draw_pile", "hand", "discard_pile", "exhaust_pile")  # the observation / boss-spec pile keys
RESTORE_ENV = "STS2_BOSSLAB_RESTORE_ENTRY_STATE"


def _card_fields(c: dict) -> dict:
    return {"id": c.get("id"), "upgrade": c.get("upgrade"), "enchantment": c.get("enchantment")}


def build_entry_record(obs: dict, *, restore_entry_state: bool = False) -> dict:
    """Capture a combat-start observation into the write-back record shape the C# hook consumes."""
    enemies = [{"id": e.get("id"), "hp": e.get("hp"), "max_hp": e.get("max_hp")}
               for e in (obs.get("enemies") or []) if e.get("id")]
    piles = [{"pile_type": pt, "cards": [_card_fields(c) for c in (obs.get(pt) or []) if c.get("id")]}
             for pt in PILE_TYPES]
    player = obs.get("player") or {}
    return {"restore_entry_state": bool(restore_entry_state), "enemies": enemies, "piles": piles,
            "relic_counters": dict(player.get("relic_counters") or {})}


def restore_flag_enabled(plan_trial: dict | None = None, env: dict | None = None) -> bool:
    """The hook is default off: it turns on only if the plan trial sets it or the env flag is a truthy '1'."""
    if env is None:
        env = os.environ
    if (plan_trial or {}).get("restore_entry_state"):
        return True
    return str(env.get(RESTORE_ENV, "")).strip() in ("1", "true", "True", "yes")


def entry_record_problems(rec: dict) -> list[str]:
    """Return integrity problems (empty list = a well-formed record the hook can consume)."""
    problems = []
    if not rec.get("enemies"):
        problems.append("no enemies recorded")
    for e in rec.get("enemies", []):
        if not e.get("id"):
            problems.append("enemy missing id")
        hp, mh = e.get("hp"), e.get("max_hp")
        if not isinstance(hp, int) or not isinstance(mh, int) or mh < 0 or hp < 0 or hp > mh:
            problems.append(f"enemy {e.get('id')} hp/max_hp out of range: hp={hp} max_hp={mh}")
    seen = set()
    for p in rec.get("piles", []):
        pt = p.get("pile_type")
        if pt not in PILE_TYPES:
            problems.append(f"unknown pile_type {pt!r}")
        elif pt in seen:
            problems.append(f"duplicate pile_type {pt!r}")
        seen.add(pt)
        for c in p.get("cards", []):
            if not c.get("id"):
                problems.append(f"card in {pt} pile missing id")
            if not isinstance(c.get("upgrade"), int):
                problems.append(f"card {c.get('id')} in {pt} pile has non-int upgrade")
    for pt in PILE_TYPES:
        if pt not in seen:
            problems.append(f"missing pile {pt!r}")
    return problems


def record_reproduces_observation(rec: dict, obs: dict) -> bool:
    """True iff the record's enemy hp/max_hp and every pile's card set match the captured observation."""
    rec_enemies = [(e["id"], e["hp"], e["max_hp"]) for e in rec.get("enemies", [])]
    obs_enemies = [(e.get("id"), e.get("hp"), e.get("max_hp")) for e in (obs.get("enemies") or []) if e.get("id")]
    if sorted(rec_enemies) != sorted(obs_enemies):
        return False
    for pt in PILE_TYPES:
        rec_cards = sorted((c["id"], c["upgrade"], str(c["enchantment"]))
                           for c in next((p["cards"] for p in rec["piles"] if p["pile_type"] == pt), []))
        obs_cards = sorted((c.get("id"), c.get("upgrade"), str(c.get("enchantment")))
                           for c in (obs.get(pt) or []) if c.get("id"))
        if rec_cards != obs_cards:
            return False
    return True
