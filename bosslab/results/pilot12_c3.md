# PILOT-12: エネルギーの経路の確定と C3（ショップ強化レリック）

ゲームは起動していない。C2走行中なのでCPUは2コア。`wt-clear5e` には触れていない。

## 1. エネルギーの経路（c3_idea.md の誤りを訂正）

- 最大エネルギー4の run は15/59（Queen入場）。うち11本は BLOOD_SOAKED_ROSE 4本・WHISPERING_EARRING 7本で、
  **すべて VAKUU イベントで取得**していた（`event_id=VAKUU`、`text_key=VAKUU.pages.INITIAL.options.*`）。
  ショップ・ボスレリック由来は0本。
- VAKUU は48回出現し、エネルギー系レリックは BLOOD_SOAKED_ROSE 7回・WHISPERING_EARRING 7回提示され、
  **14回すべて取得**している（同イベントの非エネルギー選択 FIDDLE は10回）。
  つまり `choose_event` は既にエネルギー系を最優先で取っている。CODEWIKI:476 の記述が正しく、
  c3_idea.md の「方針の外」は誤り。**エネルギーの筋は閉じた**。
- 残り4本（42A34FA0F2、50B404C802、F786F0D94E、37E263D80E）はエネルギー系レリックを持たない。
  3本は VERY_HOT_COCOA / VENERABLE_TEA_SET / EMBER_TEA を持ち、戦闘中のエネルギー増加と見られる
  （ターン2でも max_energy 4が続くため、恒久かどうかは未確定）。F786F0D94E は該当レリックも無く未解決。
  いずれも恒久の+1エネルギー源ではないので、方針で取り逃しているものではない。
- ボスレリックの選択は、15本のどれも由来ではない。ブリッジの有無を確かめる必要は薄い。

## 2. C3 の実装

- `SHOP_RELIC_SCORES` に WAR_PAINT=6、WHETSTONE=6、MOLTEN_EGG=6 を追加。6 は「強いカード・削除・ポーションが
  無いときに買う」層（既存の ORNAMENTAL_FAN 等と同じ）。
- 根拠: 272 run で WAR_PAINT 117回提示/42run、WHETSTONE 113回/40run、MOLTEN_EGG 31回/10run、購入0回。
  価格は中央値 176 / 174 / 265。所持金が足りた提示は WAR_PAINT 19回、WHETSTONE 20回、MOLTEN_EGG 0回。
- 効果の見積もり: 2枚強化で、D2（全札強化・約10枚 = Queen +8.5pt）から按分して約+1.7pt。MOLTEN_EGG は
  買える場面が0回なので実質 inert。
- 強化の扱いは `combat.py` が観測の `upgrade` フラグをそのまま読む（レリックで強化された札も次ターンから
  強化済みで渡る）。逆コンパイルは今回できていない（ゲームDLLの逆コンパイル環境を起動していない）ため、
  レリックの効果（2枚を強化）は名前と価格、既存の観測（War Paint所持runで強化枚数が多い）からの推定。

## 3. 影響の見積もり

- C1の135 seedで、この変更がショップの判断を変えるのは **7 seed（17 shop行）**。
- C2の97 seedでは 5 seed。
- C1の踏破3本: 895C061BBB と 4FDF910744 は変化なし。665CF52D37 は安価な強化レリックが2行あり得るが、
  このrunのengine採用は報酬の DEMON_FORM なので、変更で消えない。
- ゴールドの競合: 買うと後のengine札（ショップ購入）を買えなくなる可能性があるが、engine札のショップ購入は
  1runあたり0.2回程度（C1で30回/135run）なので、競合するseedは上記7件の中の一部と見られる。件数は少ない。

## 4. 実装と検証

- ブランチ `cand/engine-pack4`、worktree `~/.sts2/wt-clear5f`、base `c64851e`、commit `4d505f4`（1 commit）。
- `official_agent.py` sha256 先頭 `00823fd750a3bebd`、`combat.py` `932d286163b6071c`（C1/C2と同じ）、
  DLL は main からコピーして `592dc5411a6efda5` で一致。
- テスト: 860件中854成功・6失敗で、C2（base）と同じ6件。**新しい失敗は出ていない**。
  内容はショップ順3件と防御不足3件で、いずれもC1のengine優先に由来する既知のもの。

## 5. 留保

- 変更が効くのは7/135 seedで、全体への効果は小さい。フルrunで測るなら、その前提で。
- レリック効果の逆コンパイル確認は未実施（環境を起動していない）。
- エネルギーは方針で取り切れているので、DLL変更の提案は無し。
