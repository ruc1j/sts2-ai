"""Compare each relic our rollout model implements against its decompiled hook guard.

The RED_MASK mistake came from inferring an effect's frequency from the hook name instead of reading the
enclosing `if` in the hook body.  This prints, for every relic named in combat.py's relic constants, the
hook signature plus the guard line that follows it, so the model's own condition can be checked against it.
"""
import re, subprocess, pathlib

DECOMP = pathlib.Path("/private/var/folders/rz/wgykjn9s0wv771y8q5k77ybr0000gn/T/sts2-ai-decompiled")
RELICS_DIR = DECOMP / "MegaCrit.Sts2.Core.Models.Relics"
combat = pathlib.Path("combat.py").read_text(encoding="utf-8-sig")
names = sorted(set(re.findall(r'RELIC_([A-Z0-9_]+)\s*=\s*"RELIC\.', combat)))
print(f"combat.py が名前のある relic 定数: {len(names)} 件")
missing = []
for name in names:
    cls = "".join(part.capitalize() for part in name.lower().split("_"))
    path = RELICS_DIR / f"{cls}.cs"
    if not path.exists():
        missing.append(name)
        continue
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    hooks = []
    for i, line in enumerate(lines):
        m = re.search(r"public override async Task (BeforeCombatStart|AfterCombatEnd|BeforeSideTurnStart|AfterSideTurnStart|AfterSideTurnEnd|AfterRoomEntered|AfterObtained|AfterEnergyReset|AfterCardPlayed|AfterHandEmptied|AfterPotionProcured)\b", line)
        if not m:
            continue
        guard = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            s = lines[j].strip()
            if s.startswith("if "):
                guard = s
                break
            if s and not s.startswith("{"):
                break
        hooks.append((m.group(1), guard[:110]))
    print(f"{name}: " + " | ".join(f"{h}{(' ['+g+']') if g else ''}" for h, g in hooks[:3]))
if missing:
    print("decompile に .cs が無い:", missing)
