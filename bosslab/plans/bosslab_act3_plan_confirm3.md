# BossLab trial plan

- specs: `act3_boss_specs.jsonl` 全 180 件のうち選択条件を通ったもの 55 件から 12 件（order-seed `act3-confirm3` の hash 順、上位 12 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 80 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 12（arm 別 {'base': 12}）、offset 2..2で乱数を振る（再測定計画は別の offset 範囲を使い、実効 seed を独立させる）
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_confirm3.json`

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
