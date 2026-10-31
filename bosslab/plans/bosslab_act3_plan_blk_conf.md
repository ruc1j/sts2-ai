# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base, add2, add4（rotation 付きで spec ごとに先頭を変える）
- 選定条件: --spec-ids ファイル列挙時点の裁量（生成器は条件適用なし）
- trials: 36（arm 別 {'base': 12, 'add2': 12, 'add4': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 9 trial（RELIC.STONE_CRACKER）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_blk_conf.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 4c69c357dcda | 76 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base, add2, add4 |
| e75781521da8 | 75 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base, add2, add4 |
| 60058beedf0a | 70 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base, add2, add4 |
| 5b3328eda1dc | 121 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base, add2, add4 |
| 4bb6cf77fdd9 | 77 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 27 | 負 | base, add2, add4 |
| eb8756252bb6 | 67 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base, add2, add4 |
| fef5e8158e35 | 46 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 22 | 負 | base, add2, add4 |
| b37c3498e7f8 | 70 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base, add2, add4 |
| 75495c03f631 | 33 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 21 | 負 | base, add2, add4 |
| fd39a3b868b5 | 69 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 22 | 負 | base, add2, add4 |
| 614271466f56 | 73 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 20 | 負 | base, add2, add4 |
| c589d7860c35 | 53 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 18 | 負 | base, add2, add4 |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
