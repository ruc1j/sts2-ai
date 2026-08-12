import unittest

from act_map import matching_paths, paths


class ActMapTest(unittest.TestCase):
    def test_enumerates_branches(self) -> None:
        data = {
            "points": [
                {"id": "0:0", "row": 0, "type": "Ancient", "children": ["0:1", "1:1"]},
                {"id": "0:1", "row": 1, "type": "Monster", "children": ["0:2"]},
                {"id": "1:1", "row": 1, "type": "Unknown", "children": ["0:2"]},
                {"id": "0:2", "row": 2, "type": "Boss", "children": []},
            ]
        }
        self.assertEqual(len(paths(data)), 2)
        self.assertEqual(len(matching_paths(data, ["ancient", "monster", "boss"])), 1)


if __name__ == "__main__":
    unittest.main()
