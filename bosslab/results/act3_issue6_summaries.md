# issue #6 要約（TEST_SUBJECT 見積もり / H3 設計）

## TEST_SUBJECT の BossLab 見積もり（issue #6 転記用）

- TEST_SUBJECT は BossLab と combat.py で機械的に扱える（run は encounter 汎用、RESPAWN_MOVE 二段復活と Adaptable/Enrage を実装済、enemies_glory.json に形態 100/200/300）。
- 主障壁は忠実な entry spec の不在: 新しい agent 形式（pile 付き）の TEST_SUBJECT 入室観測は 0 件、control 蓄積 136 本の Act3 ボス到達も 33/33 QUEEN で TEST_SUBJECT 0。
- 到達済みの古い trace 約 10 本は relic/deck/draw/discard/exhaust/enchantment/敵 max_hp が無く、BossLab の固定 entry を復元できない。
- 次の goal: TEST_SUBJECT に routing する既知 seed で新形式の走行を集め（実行は leader）、QUEEN 専用の判定ツールを 3 形態（累計 600 HP / 形態処理数）に一般化。詳細 act3_test_subject_lab_estimate.md（コミット 1557d38）。

## H3 設計（Amalgam を実際に削る保証、issue #6 転記用）

- dev2 で「Amalgam を倒せる状況では優先」は実質未試行: H1（実効 HP ≤50）/H2（次手番の一撃が自分を殺しうる）は条件が「Amalgam が既に低い」前提を含み、Queen 優先だと発火せず queenfirst に収束（Amalgam 撃破 0/12）。
- 削りを保証する 2 案（次 goal）: H3a=序盤 N ターンだけ Amalgam（手番基準で必ず発火）、H3c=Amalgam の予想被ダメが生存の割超の間だけ Amalgam（脅威基準で必ず発火）。診断の H3b（閾値 150）は live で 150 に届かず queenfirst 収束。
- 総火力/ターンは毎ターンの出力がエネルギー律速なのでほぼ不変。動くのは出力の割き先と Amalgam 早処理による生存/削り（H3a: Queen 削り ↓・生存 ↑、H3c: Amalgam 撃破 ↑↑・生存 ↑）。
- 実測は confirm4 の新規 panel で base/H1/H3a/H3c を同一 entry 配対、判定は事前登録規則（コミット 4693f2e）のまま。詳細 act3_hybrid_h3_design.md（コミット 50c5b1e）。
