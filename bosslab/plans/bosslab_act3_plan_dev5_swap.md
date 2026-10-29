# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base（単一 arm なので rotation なし）
- 選定条件: dev5 swap: fid5入場忠実性で不一致の 8aa46daede55(RELIC.FORGOTTEN_SOUL・入室前のexhaust所持)/ e030d2f11e5f(RELIC.BLESSED_ANTLER) を、dev5-split hash順で同一band・lossの 3bb38a1da0b5 / 96c9cc444c23 に差し替え。confirm5 と used.speclist とは非重複
- trials: 12（arm 別 {'base': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 1 trial（RELIC.STONE_CRACKER）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_dev5_swap.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 09e1ef74cb7c | 85 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 勝 | base |
| a362ff6f5e4e | 85 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 勝 | base |
| 74062b5e0d2d | 103 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 22 | 勝 | base |
| 3bb38a1da0b5 | 80 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 29 | 負 | base |
| 96c9cc444c23 | 64 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base |
| eb8756252bb6 | 67 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base |
| d416e73f2d0b | 78 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 29 | 負 | base |
| 4c69c357dcda | 76 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| fef5e8158e35 | 46 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 22 | 負 | base |
| d22ed45bc52f | 53 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 29 | 負 | base |
| 62f27302ec36 | 44 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 28 | 負 | base |
| e8b1b9347232 | 56 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 23 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
