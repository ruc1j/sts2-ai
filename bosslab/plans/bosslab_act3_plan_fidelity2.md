# BossLab trial plan

- specs: `bosslab_act3_fidelity2.specs.jsonl` 全 3 件のうち選択条件を通ったもの 3 件から 3 件（order-seed `act3-fidelity2` の hash 順、上位 3 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 2 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 3（arm 別 {'base': 3}）、offset 0..0で乱数を振る
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_fidelity2.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 3e7eb2812625 | 87 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 勝 | base |
| 161e7059ac92 | 100 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 勝 | base |
| 9596f14efcee | 72 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 27 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
