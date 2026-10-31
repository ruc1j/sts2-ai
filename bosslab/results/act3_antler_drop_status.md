# BLESSED_ANTLER のpile落とし改修: 状況（2026-10-31）

- 変更: `BossLab.RestoreRecordedPiles` を、記録のカードが全て生きたインスタンスに対応した場合（unmatched == 0）だけ、記録のpileに無いインスタンス（入場hookが足したDazed等）を捨てるようにした。対応できなかった記録カードがあるときは従来どおり山札の先頭へ戻す。ビルドは警告0、エラー0。
- 確認できたこと: 回帰として FORGOTTEN_SOUL の spec 8aa46daede55（fid8 trial 0）は完走し、pile再構築のログも出た（Hand:3, Draw:23, Discard:0, Exhaust:1）。
- 結果（Steam起動後の再実行 fid9）: BLESSED_ANTLER の spec e030d2f11e5f は「dropped 3 unrecorded hook-added card(s)」のログが出て、山札が24、手札3になり、`bosslab_fidelity.py` で lab vs spec が一致した（`act3_fid9_fidelity.md`）。fid7で唯一の不一致だった trial 10 が解消したので、書き戻しありの忠実性は12/12（fid7の11件と今回の1件の合算、再実行は1 trialのみ）。
- 回帰: FORGOTTEN_SOUL の spec 8aa46daede55 は fid8 で完走（`act3_fid8_fidelity.md`）。
- 留保: 12 specを一度に流し直したわけではない（fid7の11件は旧DLLの結果）。改修後DLLで全12 specを回す再照合は未実施。ミッド戦の停止（fid7 trial 5）は別件で未解決。
- 運用メモ: Steamクライアントが終了していると `SteamAPI_Init() failed` で起動に失敗する。その失敗が `mods/Sts2Ai` を残す場合があり、次回は `ANOMALY: stale mod install` で止まる。残骸を消してから再実行する。

## 改修後DLLでの12 spec通し再照合（fid10、2026-10-31）

`bosslab_act3_plan_fid7.json`（同じ12 spec、書き戻しあり）を改修後のDLLで流し直した。`act3_fid10_fidelity.md`。

- 入場状態は12 spec全てで lab vs spec が一致した（fid7の11/12から12/12）。BLESSED_ANTLER の trial 10 も一致。
- trial 5（spec 96c9cc444c23）は、fid7と同じく2ターン目以降で更新が320秒止まり、結果行が出なかった（lab_results 11行、failures 2行）。fid7に続く再現なので、書き戻しやこの改修の副作用ではなく、このspecの戦闘中の停止と見る。入場状態の照合は取れている。
- 留保: 一致は入場状態の項目（敵HP、pile、デッキ、HP）であり、戦闘結果の再現ではない。ラボ上の勝敗の絶対値は実走と一致しない。
