# BossLab trial plan

- specs: `act3_boss_specs.jsonl` 全 180 件のうち選択条件を通ったもの 80 件から 12 件（order-seed `act3-dev2` の hash 順、上位 12 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 80 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 12（arm 別 {'base': 12}）、offset 0..0で乱数を振る
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_dev2.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 8e975fbdaf50 | 78 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 21 | 負 | base |
| 8dbc5b8364c2 | 99 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 32 | 負 | base |
| b91b92466c0c | 60 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base |
| f7fe72c3ee32 | 49 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| b947d020207e | 68 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |
| f19fb10979bf | 78 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 65702aa4710f | 79 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| 6fb9597984bb | 75 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| 0b21d5e5cd2a | 76 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 28 | 負 | base |
| 9c9b148472cd | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 5731321317b5 | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| fecbbdef1fc0 | 74 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 30 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
