from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_map(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as file:
        data = json.load(file)
    points = {point["id"]: point for point in data["points"]}
    if len(points) != len(data["points"]):
        raise ValueError("duplicate map point")
    for point in points.values():
        for child in point["children"]:
            if child not in points:
                raise ValueError(f"missing child: {child}")
            if points[child]["row"] != point["row"] + 1:
                raise ValueError(f"non-adjacent edge: {point['id']} -> {child}")
    return data


def paths(data: dict) -> list[tuple[str, ...]]:
    points = {point["id"]: point for point in data["points"]}
    start = next(point for point in points.values() if point["type"] == "Ancient")
    result: list[tuple[str, ...]] = []

    def visit(point_id: str, path: tuple[str, ...]) -> None:
        point = points[point_id]
        path += (point_id,)
        if point["type"] == "Boss":
            result.append(path)
            return
        for child in point["children"]:
            visit(child, path)

    visit(start["id"], ())
    return result


def matching_paths(data: dict, room_types: list[str]) -> list[tuple[str, ...]]:
    points = {point["id"]: point for point in data["points"]}
    normalize = lambda value: re.sub(r"[^a-z]", "", value.lower())
    expected = list(map(normalize, room_types))
    return [
        path
        for path in paths(data)
        if [normalize(points[point_id]["type"]) for point_id in path] == expected
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a map exported from the installed STS2 DLL")
    parser.add_argument("map_json")
    parser.add_argument("--show-path", action="store_true")
    parser.add_argument("--history", help="STS2 .run file; verifies its Act 1 route against the map")
    args = parser.parse_args()
    data = load_map(args.map_json)
    all_paths = paths(data)
    print(
        f"version={data['game_version']} seed={data['seed']} act={data['act']} "
        f"points={len(data['points'])} paths={len(all_paths)}"
    )
    if args.show_path and all_paths:
        points = {point["id"]: point for point in data["points"]}
        print(" -> ".join(f"{point_id}({points[point_id]['type']})" for point_id in all_paths[0]))
    if args.history:
        with open(args.history, encoding="utf-8-sig") as file:
            history = json.load(file)
        route_types = [entry["map_point_type"] for entry in history["map_point_history"][0]]
        matches = matching_paths(data, route_types)
        print(f"history_matches={len(matches)}")
        if len(matches) != 1:
            raise SystemExit("history route did not uniquely match the generated map")
        print("history_path=" + " -> ".join(matches[0]))


if __name__ == "__main__":
    main()
