# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 0 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
- arms: base（単一 arm なので rotation なし）
- 選定条件: confirm5 swap: CROSSBOW持しの bbbfd4fc2927（入場忠実性で開示handがずれる系統）を、confirm5-split hash順で原因レリックなし・lossの d48032980ad0 に差し替え。ただし新形式usableで原因レリックなしのlossはband>=80にしか残っておらず、bbbfdのband(<60)とはbandが変わる（同じbandのlossが存在しない）。fid5/dev5_swap とは非重複、win0維持
- trials: 12（arm 別 {'base': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 0 trial（なし）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_confirm5_swap.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 0256297739fc | 92 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |
| bf5c0080839c | 97 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 21 | 負 | base |
| 75157844a09c | 114 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base |
| c247ea1ceac4 | 90 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| 12d699c2fb1a | 72 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| 98ab6c77b59b | 72 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 27 | 負 | base |
| ca23400bbcc3 | 78 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 28 | 負 | base |
| e75781521da8 | 75 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 26 | 負 | base |
| 69d5563583a3 | 56 | TORCH_HEAD_AMALGAM:198/QUEEN:399 | 25 | 負 | base |
| b28169a712aa | 58 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 28 | 負 | base |
| c589d7860c35 | 53 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 18 | 負 | base |
| d48032980ad0 | 95 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 31 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
