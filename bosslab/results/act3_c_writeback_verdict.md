# 第1段階（C）: 入場状態の書き戻しの検証と判定

## 結論

判定は「採用」（条件つき）。書き戻しを有効にした再照合（fid7）は、同じ12 specで11/12が入場状態の全項目で一致し、無効のfid5の10/12を下回らなかった。

## 手順

- `make_bosslab_plan.py` に `--restore-entry-state` を追加した（既定は無効で、無指定の計画は従来とバイト単位で同一）。有効にすると、各trialに記録済みの敵HP（`enemies`）とcombat pile（`piles`）を載せ、`restore_entry_state: true` を立てる。テストは `test_bosslab_plan.py` に1件追加した。
- 実機ビルドは1回（コンパイル警告0、エラー0）。書き戻しの処理（BossLab.cs、20892cd）は無修正で通った。
- 計画は `bosslab/plans/bosslab_act3_plan_fid7.json`。specはfid5と同じ12件で、trialの他の項目はfid5と一致している（書き戻しの3項目だけが違う）。実機で `official_agent.py` を使い、12 trialを流した。比較は `bosslab_fidelity.py`（結果は `act3_fid7_fidelity.md`）。

## 結果

| 計画 | 一致 | 不一致 |
| --- | --- | --- |
| fid5（書き戻しなし） | 10 / 12 | trial 9（spec 8aa46daede55、敵HP）、trial 10（spec e030d2f11e5f、Dazed） |
| fid7（書き戻しあり） | 11 / 12 | trial 10（spec e030d2f11e5f）のみ |

- trial 9（敵HPのずれ、レリックの入場効果の二重発火）は、書き戻しで一致するようになった。
- trial 10は引き続き不一致だった。labの手札が3、山札が27で、specは山札24。labだけにDazedが3枚多い（`deck.multiset: lab={DAZED+0+: 3} / spec={}`）。書き戻しの処理は、記録のpileに入っていないインスタンスを「元の相対順で山札の先頭に戻す」ため、入場hookが追加したDazedが残る。BLESSED_ANTLERを持つspecには、この書き戻しは効かない。
- 残った対策: BLESSED_ANTLERを持つspecは、これまでどおり選定から除外する。記録のpileにないインスタンスを捨てる改修は、実機ビルドをもう1回要するため、このgoalでは行わない（「実機ビルドは1回」の条件）。

## 留保

- 標本は12 specで、1件の改善（10/12→11/12）に過ぎない。「書き戻しが効く」の根拠は、trial 9の1件と、全trialでpile再構築のログが出ていることである。
- fid7のtrial 5（spec 96c9cc444c23）は、2ターン目の `end_turn` のあとで更新が320秒止まり、タイムアウトで結果行が出なかった（lab_results 11行、failures 2）。入場状態は一致しているため、入場後の戦闘中の散発的な停止と見ている（fid5では同じspecが完走した）。書き戻しが原因かどうかは、この1件では切り分けられていない。
- 次の第2段階（A）の対照実験では、足したカードが山札の先頭に置かれるのを避けるため、書き戻しは使わない（全アームで無効、BLESSED_ANTLERとFORGOTTEN_SOULを持つspecは除外）。そのため、Cの採用は第2段階の結果には影響しない。
