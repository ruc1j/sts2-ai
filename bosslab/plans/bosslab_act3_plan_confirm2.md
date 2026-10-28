# BossLab trial plan

- specs: `act3_boss_specs.jsonl` 全 180 件のうち選択条件を通ったもの 68 件から 12 件（order-seed `act3-confirm2` の hash 順、上位 12 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 80 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 12（arm 別 {'base': 12}）、offset 2..2で乱数を振る（再測定計画は別の offset 範囲を使い、実効 seed を独立させる）
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_confirm2.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| b05bd018dc94 | 40 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 28 | 負 | base |
| 94149577e75a | 65 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| 494896fc3794 | 78 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 30 | 負 | base |
| 51d0afcd026a | 99 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |
| 867e4dad6aa9 | 77 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 3e7eb2812625 | 87 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 勝 | base |
| a8f496156299 | 94 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 28 | 負 | base |
| 54912dc867a3 | 97 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 勝 | base |
| 4744505c73ad | 52 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |
| a3a103860f92 | 99 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |
| 50fd0da56913 | 57 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 30 | 負 | base |
| ddb0e68f6ef4 | 83 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
