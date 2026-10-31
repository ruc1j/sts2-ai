# BossLab trial plan

- specs: `--spec-ids` による手動選択 6 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base, add2, add4（rotation 付きで spec ごとに先頭を変える）
- 選定条件: --spec-ids ファイル列挙時点の裁量（生成器は条件適用なし）
- trials: 18（arm 別 {'base': 6, 'add2': 6, 'add4': 6}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 3 trial（RELIC.STONE_CRACKER）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_blk_dev.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 3bb38a1da0b5 | 80 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 29 | 負 | base, add2, add4 |
| d22ed45bc52f | 53 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 29 | 負 | base, add2, add4 |
| 30c98f643174 | 97 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 26 | 負 | base, add2, add4 |
| 16d838af30eb | 76 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 22 | 負 | base, add2, add4 |
| 0be389384303 | 72 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base, add2, add4 |
| a4f376cd945f | 87 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base, add2, add4 |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
