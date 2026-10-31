# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base, noshrug（rotation 付きで spec ごとに先頭を変える）
- 選定条件: --spec-ids ファイル列挙時点の裁量（生成器は条件適用なし）
- trials: 24（arm 別 {'base': 12, 'noshrug': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 0 trial（なし）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act2_plan_ns_conf.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| b1a85c7a9eee | 40 | THE_INSATIABLE:321 | 24 | 負 | base, noshrug |
| 0bee355cb23b | 86 | THE_INSATIABLE:321 | 24 | 負 | base, noshrug |
| 0395112a9828 | 80 | THE_INSATIABLE:321 | 22 | 負 | base, noshrug |
| b14a4126ee40 | 40 | THE_INSATIABLE:321 | 22 | 負 | base, noshrug |
| f3374cf1f6a3 | 90 | THE_INSATIABLE:321 | 18 | 勝 | base, noshrug |
| 401c5b9edb0e | 80 | THE_INSATIABLE:321 | 23 | 勝 | base, noshrug |
| 346ec700b880 | 85 | THE_INSATIABLE:318 | 21 | 勝 | base, noshrug |
| 486f888293cc | 57 | THE_INSATIABLE:321 | 21 | 負 | base, noshrug |
| ae8974f4b753 | 80 | THE_INSATIABLE:321 | 26 | 勝 | base, noshrug |
| 412d63e4be9e | 80 | THE_INSATIABLE:321 | 20 | 負 | base, noshrug |
| b411c1748867 | 70 | THE_INSATIABLE:318 | 25 | 負 | base, noshrug |
| cbe3ca1b66d8 | 73 | THE_INSATIABLE:321 | 25 | 勝 | base, noshrug |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
