import unittest
import importlib.util
from pathlib import Path

# Unit tests for the H3a (序盤 Amalgam 削り, QUEENFIRST_H3_OPEN_TURNS) and H3c (危険前に削り,
# QUEENFIRST_H3_DANGER_FRAC) candidate agents. They drive the generated agents' real choose() on a
# synthetic Queen+Amalgam observation and assert which enemy the single-target attack aims at, before
# any real-machine run. Only the target choice differs from the base, so target_id is the whole
# behavior under test. Self-contained (no gitignored dev2 traces).
_TOOLS = Path(__file__).resolve().parent
_AG = _TOOLS / "bosslab" / "agents"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H3A = load("h3a_under_test", _AG / "official_agent_H3a.py")
H3C = load("h3c_under_test", _AG / "official_agent_H3c.py")


def make_obs(turn=1, amalgam_hp=199, amalgam_incoming=18, queen_incoming=18,
             hp=100, block=0, energy=3, keep_amalgam=True, keep_queen=True):
    """A minimal but legal Queen-fight first observation: one Strike that may hit the Amalgam or the Queen."""
    enemies = []
    if keep_amalgam:
        enemies.append({"combat_id": "A1", "id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": amalgam_hp,
                        "max_hp": 199, "block": 0, "intents": [{"damage": amalgam_incoming, "repeats": 1}],
                        "powers": []})
    if keep_queen:
        enemies.append({"combat_id": "Q1", "id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400,
                        "block": 0, "intents": [{"damage": queen_incoming, "repeats": 1}], "powers": []})
    legal_targets = ([t for t in ("A1", "Q1") if (t == "A1" and keep_amalgam) or (t == "Q1" and keep_queen)]
                     or ["A1"])
    return {
        "phase": "combat", "turn": turn, "enemies": enemies,
        "hand": [{"index": 0, "card_id": "CARD.STRIKE", "type": "Attack", "cost": 1, "upgrade": 0,
                  "vars": [{"id": "Damage", "value": 9}]}],
        "legal_actions": [{"type": "card", "card_id": "CARD.STRIKE", "hand_index": 0, "target_id": t}
                          for t in legal_targets],
        "player": {"hp": hp, "max_hp": 113, "block": block, "energy": energy, "powers": [], "relics": []},
        "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "potions": [],
    }


def chosen_target(agent, obs):
    agent._PENDING_ACTION = None
    action = agent.choose(dict(obs))
    return action.get("target_id"), action.get("decision_source")


class H3aTest(unittest.TestCase):
    def test_chips_amalgam_on_first_opening_turn(self):
        tid, src = chosen_target(H3A, make_obs(turn=1))
        self.assertEqual(tid, "A1")
        self.assertTrue(src.startswith("queen_minion_h3a"))  # fired by the H3a focus branch, not fallback

    def test_chips_amalgam_at_turn_equal_to_N(self):
        tid, _ = chosen_target(H3A, make_obs(turn=H3A.QUEENFIRST_H3_OPEN_TURNS))
        self.assertEqual(tid, "A1")

    def test_turn_after_N_targets_queen(self):
        tid, _ = chosen_target(H3A, make_obs(turn=H3A.QUEENFIRST_H3_OPEN_TURNS + 1))
        self.assertEqual(tid, "Q1")

    def test_deep_turn_targets_queen(self):
        tid, _ = chosen_target(H3A, make_obs(turn=4))
        self.assertEqual(tid, "Q1")

    def test_chips_at_full_amalgam_hp_guarantees_chip_not_low_hp_gate(self):
        # Amalgam still at its entry 199 -> H3a still chips on turn 1. This is the point vs H1: the
        # trigger is turn-based, not "the Amalgam is already low", so it cannot self-lock.
        tid, _ = chosen_target(H3A, make_obs(turn=1, amalgam_hp=199))
        self.assertEqual(tid, "A1")

    def test_self_limits_to_queen_when_amalgam_gone(self):
        # No Amalgam left -> eff hp 0 -> focus false -> aim the Queen (self-limiting, no wasted chip).
        tid, src = chosen_target(H3A, make_obs(turn=1, keep_amalgam=False))
        self.assertEqual(tid, "Q1")
        self.assertTrue(src.startswith("queen_minion_h3a"))

    def test_only_arms_when_queen_present(self):
        # With only an Amalgam on the board (no Queen) the Queen-focus short-circuit does not engage
        # (queen_present false), so it is not the H3a branch deciding the target -> heuristic fallback.
        tid, src = chosen_target(H3A, make_obs(turn=1, keep_amalgam=True, keep_queen=False))
        self.assertFalse(src.startswith("queen_minion_h3a"))


class H3cTest(unittest.TestCase):
    def test_safe_turn_targets_queen(self):
        # Amalgam incoming 8 < 0.5*(hp100+blk0)=50 -> Queen.
        tid, src = chosen_target(H3C, make_obs(turn=1, amalgam_incoming=4, queen_incoming=4))
        self.assertEqual(tid, "Q1")
        self.assertTrue(src.startswith("queen_minion_h3c"))

    def test_dangerous_turn_chips_amalgam(self):
        # Amalgam incoming 120 >= 0.5*100=50 -> chip the Amalgam.
        tid, _ = chosen_target(H3C, make_obs(turn=1, amalgam_incoming=120, queen_incoming=0))
        self.assertEqual(tid, "A1")

    def test_boundary_inclusive_arms_at_exactly_half(self):
        # Rule uses >= : incoming exactly 50 == 0.5*100 arms the chip.
        tid, _ = chosen_target(H3C, make_obs(turn=1, amalgam_incoming=50, queen_incoming=0))
        self.assertEqual(tid, "A1")

    def test_just_below_boundary_targets_queen(self):
        # incoming 49 < 0.5*100=50 -> Queen (strict on the below side).
        tid, _ = chosen_target(H3C, make_obs(turn=1, amalgam_incoming=49, queen_incoming=0))
        self.assertEqual(tid, "Q1")

    def test_block_raises_threshold_survival_scaled(self):
        # hp100+block60=160 survival, threshold 0.5*160=80; Amalgam incoming 40 < 80 -> Queen. Block
        # makes the player safer so it need not spend the turn killing the Amalgam.
        tid, _ = chosen_target(H3C, make_obs(turn=1, amalgam_incoming=40, queen_incoming=0, block=60))
        self.assertEqual(tid, "Q1")

    def test_self_limits_to_queen_when_amalgam_gone(self):
        # No Amalgam -> its incoming 0 < 0.5*survival -> Queen (and eff hp 0 arms nothing).
        tid, _ = chosen_target(H3C, make_obs(turn=1, keep_amalgam=False, queen_incoming=40))
        self.assertEqual(tid, "Q1")

    def test_arms_on_first_turn_independent_of_amalgam_hp(self):
        # Full-HP Amalgam (199) but dangerous incoming -> chips on turn 1. Threat-armed, so unlike H1 it
        # does not presuppose the Amalgam is already low, and it guarantees chipping.
        tid, _ = chosen_target(H3C, make_obs(turn=1, amalgam_hp=199, amalgam_incoming=120, queen_incoming=0))
        self.assertEqual(tid, "A1")


if __name__ == "__main__":
    unittest.main()
