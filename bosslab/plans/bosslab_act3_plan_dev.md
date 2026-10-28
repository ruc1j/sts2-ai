# BossLab trial plan

- specs: `act3_boss_specs.jsonl` 全 173 件のうち選択条件を通ったもの 111 件から 12 件（order-seed `act3-dev` の hash 順、上位 12 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 111 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 12（arm 別 {'base': 12}）、offset 0..0で乱数を振る
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_dev.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 5fc87b6d496b | 79 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 07963ad93703 | 122 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 25 | 負 | base |
| 06270e7c70af | 45 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 28 | 負 | base |
| d4c9f1140457 | 144 | TORCH_HEAD_AMALGAM:198/QUEEN:400 | 32 | 負 | base |
| f19fb10979bf | 78 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| b91b92466c0c | 60 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base |
| 69d5563583a3 | 56 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 25 | 負 | base |
| f8f7a8c4d489 | 85 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 28 | 負 | base |
| b9b8473f7bb2 | 139 | TORCH_HEAD_AMALGAM:199/QUEEN:399 | 32 | 負 | base |
| 1ab8aedd3250 | 40 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| ce97488f1b73 | 76 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 19 | 負 | base |
| 4744505c73ad | 52 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
