from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMMANDS = (
    "DamageCmd.Attack",
    "CreatureCmd.GainBlock",
    "CreatureCmd.Heal",
    "CreatureCmd.Add",
    "CreatureCmd.Escape",
    "CreatureCmd.Kill",
    "CreatureCmd.SetMaxAndCurrentHp",
    "PowerCmd.Apply",
    "PowerCmd.Remove",
    "CardPileCmd.AddToCombatAndPreview",
    "CardPileCmd.AddGeneratedCardToCombat",
)


def _balanced(text: str, start: int, opening: str = "(", closing: str = ")") -> tuple[str, int]:
    depth = 0
    quote = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    raise ValueError("unbalanced source")


def _method_body(source: str, method: str) -> str:
    match = re.search(rf"\b[\w<>?]+\s+{re.escape(method)}\s*\(", source)
    if not match:
        raise ValueError(f"method not found: {method}")
    brace = source.find("{", match.end())
    return _balanced(source, brace, "{", "}")[0]


def _arguments(value: str) -> list[str]:
    result, start, depth, quote = [], 0, 0, None
    for index, char in enumerate(value):
        if quote:
            if char == quote and value[index - 1] != "\\":
                quote = None
        elif char in "\"'":
            quote = char
        elif char in "(<[{":
            depth += 1
        elif char in ")>]}":
            depth -= 1
        elif char == "," and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return result


def effects(source: str, method: str) -> list[dict]:
    body = _method_body(source, method)
    found: list[tuple[int, dict]] = []
    for command in COMMANDS:
        pattern = re.compile(re.escape(command) + r"(?:<(?P<model>[^>]+)>)?\s*\(")
        for match in pattern.finditer(body):
            arguments, _ = _balanced(body, match.end() - 1)
            args = _arguments(re.sub(r"\s+", " ", arguments))
            effect = {"command": command, "arguments": args}
            if match.group("model"):
                effect["model"] = match.group("model")
            if command == "DamageCmd.Attack":
                effect["amount"] = args[0]
            elif command == "CreatureCmd.GainBlock":
                effect.update(target=args[0], amount=args[1])
            elif command == "PowerCmd.Apply":
                effect.update(target=args[1], amount=args[2])
            found.append((match.start(), effect))
    return [effect for _, effect in sorted(found, key=lambda item: item[0])]


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach decompiled monster move effects to exported STS2 data")
    parser.add_argument("enemy_json")
    parser.add_argument("decompiled_dir")
    parser.add_argument("--output")
    args = parser.parse_args()
    path = Path(args.enemy_json)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    source_root = Path(args.decompiled_dir) / "MegaCrit.Sts2.Core.Models.Monsters"
    for monster in data["monsters"]:
        source = (source_root / f"{monster['class']}.cs").read_text(encoding="utf-8-sig")
        if "GenerateMoveStateMachine" not in source:
            continue
        machine_source = _method_body(source, "GenerateMoveStateMachine")
        move_vars = {
            variable: state_id
            for _, variable, state_id in re.findall(r'(\w+State)\s+(\w+)\s*=\s*new \w+State\("([^"]+)"', machine_source)
        }
        conditions = [
            [move_vars[variable], condition]
            for variable, condition in re.findall(r"\.AddState\((\w+),\s*\(\)\s*=>\s*(.+)\);", machine_source)
            if variable in move_vars
        ]
        for state in monster["states"]:
            if method := state.get("perform"):
                state["effects"] = effects(source, method)
            if state["type"] == "ConditionalBranchState":
                for branch in state["branches"]:
                    match = next((item for item in conditions if item[0] == branch["state"]), None)
                    if not match:
                        continue
                    branch["condition"] = match[1]
                    conditions.remove(match)
    output = Path(args.output) if args.output else path
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
