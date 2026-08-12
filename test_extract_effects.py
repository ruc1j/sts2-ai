import unittest

from extract_effects import _method_body, effects


class ExtractEffectsTest(unittest.TestCase):
    def test_extracts_power_and_damage(self) -> None:
        source = """
        private async Task Move(IReadOnlyList<Creature> targets) {
            await DamageCmd.Attack(Damage).FromMonster(this).Execute(null);
            await PowerCmd.Apply<StrengthPower>(ctx, base.Creature, 7m, base.Creature, null);
        }
        """
        result = effects(source, "Move")
        self.assertEqual(result[0]["amount"], "Damage")
        self.assertEqual(result[1]["model"], "StrengthPower")
        self.assertEqual(result[1]["amount"], "7m")

    def test_finds_non_task_method(self) -> None:
        self.assertEqual(_method_body("private Machine Build() { return value; }", "Build").strip(), "return value;")


if __name__ == "__main__":
    unittest.main()
