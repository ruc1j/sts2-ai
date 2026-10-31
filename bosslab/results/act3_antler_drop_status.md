# BLESSED_ANTLER のpile落とし改修: 状況（2026-10-31）

- 変更: `BossLab.RestoreRecordedPiles` を、記録のカードが全て生きたインスタンスに対応した場合（unmatched == 0）だけ、記録のpileに無いインスタンス（入場hookが足したDazed等）を捨てるようにした。対応できなかった記録カードがあるときは従来どおり山札の先頭へ戻す。ビルドは警告0、エラー0。
- 確認できたこと: 回帰として FORGOTTEN_SOUL の spec 8aa46daede55（fid8 trial 0）は完走し、pile再構築のログも出た（Hand:3, Draw:23, Discard:0, Exhaust:1）。
- 未確認: 本命の BLESSED_ANTLER の spec e030d2f11e5f は、fid8 trial 1 が起動せず（Steam初期化エラー）、単独の再実行 fid9 もSteamクライアントが終了していて `SteamAPI_Init() failed` で止まったため、Dazedが消えるかは測れていない。
- 次の手順: Steamを起動してから `bosslab/plans/bosslab_act3_plan_fid8.json` の trial 1 だけを再実行し、`bosslab_fidelity.py` で deck.multiset が一致するか見る。一致すれば忠実性は12/12。
