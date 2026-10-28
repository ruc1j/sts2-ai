# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base（単一 arm なので rotation なし）
- 選定条件: confirm3 と同一の12 spec（順不同）。defer_relics / 入場HP / ポーション枠の忠実性修正を確かめるための再走査 panel。
- trials: 12（arm 別 {'base': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 1 trial（RELIC.STONE_CRACKER）、開手札がlab で再現できない flag が 1 trial（RELIC.CROSSBOW）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_confirm3_fixed.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| bf5c0080839c | 97 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 21 | 負 | base |
| 897931d3b0da | 74 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 28 | 負 | base |
| 83e6a3465fde | 79 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| 703d7333c072 | 77 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 30 | 負 | base |
| 1a05bb73e94b | 90 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 32 | 負 | base |
| c77f7c059684 | 85 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 28 | 負 | base |
| f737cab6f8b6 | 94 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 624ae0d1306b | 90 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base |
| e75781521da8 | 75 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base |
| 739389f7cb7f | 101 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| 59ed603b4b73 | 90 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| bbbfd4fc2927 | 59 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 28 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
