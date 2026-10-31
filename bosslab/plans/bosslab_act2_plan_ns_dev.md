# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base, noshrug（rotation 付きで spec ごとに先頭を変える）
- 選定条件: --spec-ids ファイル列挙時点の裁量（生成器は条件適用なし）
- trials: 24（arm 別 {'base': 12, 'noshrug': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 0 trial（なし）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act2_plan_ns_dev.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| dbfcde8ae751 | 85 | THE_INSATIABLE:321 | 21 | 勝 | base, noshrug |
| dbe0014239e9 | 91 | THE_INSATIABLE:321 | 23 | 勝 | base, noshrug |
| 02ce63e28656 | 102 | THE_INSATIABLE:318 | 21 | 負 | base, noshrug |
| 520b6026f1ef | 87 | THE_INSATIABLE:321 | 25 | 負 | base, noshrug |
| 42b0443e2e93 | 71 | THE_INSATIABLE:321 | 18 | 負 | base, noshrug |
| 770594549113 | 58 | THE_INSATIABLE:321 | 26 | 負 | base, noshrug |
| 25e4bda4047b | 80 | THE_INSATIABLE:321 | 20 | 勝 | base, noshrug |
| 7ab8203130bd | 73 | THE_INSATIABLE:321 | 21 | 負 | base, noshrug |
| 99848c8a2a05 | 44 | THE_INSATIABLE:321 | 21 | 負 | base, noshrug |
| e794f34a10c7 | 56 | THE_INSATIABLE:321 | 21 | 勝 | base, noshrug |
| 6f46d84367c0 | 69 | THE_INSATIABLE:318 | 18 | 勝 | base, noshrug |
| 1f92269cca69 | 78 | THE_INSATIABLE:321 | 22 | 勝 | base, noshrug |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
