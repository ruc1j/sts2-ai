# Mad Scienceの基礎値とカード種別

## 正しさの修正

v0.107.1の`MadScience.ExecuteAttack`は基礎Damageを通常の攻撃コマンドへ渡す。手札のPreviewValueにはプレイヤーのStrengthやWeakが既に反映されるが、以前のモデルはその表示値へStrengthを足し、敵のVulnerableも通していなかった。

固定比較の候補N8では、seq403の表示Damage16・Strength4・敵Vulnerableに対し、モデルが20ダメージ、ゲームが24ダメージだった。seq476ではVulnerableがなく、同じ二重加算が4ダメージの過大評価になっていた。

Bridgeから`base_value`を出力し、基礎値と表示値を分けて取り込む。旧traceはMad Scienceの標準値Damage12・Block8に戻す。ゲームの強化はInnateを付けるだけなので、通常攻撃の強化ダメージは加えない。

Attack版は共通の攻撃処理へ通し、Strength、Weak、Vulnerable、Pen Nib、複数回使用、反撃、撃破処理を適用する。SappingはWeak→Vulnerableの順でArtifactを消費する。Skill版はDexterity・FrailとSkillのカウンターを、Power版はPowerの割引・発動回数・使用後に戦闘から消える処理を適用する。

Mad Scienceの種類・追加効果・基礎値を山札・捨て札・廃棄札でも保持する。Attack版をSecond WindでSkill扱いして廃棄するなど、種類を固定名だけで判断していた箇所も、このコピーの実際の種類を使う。Chaosのランダム生成とCurious/Improvement版の新規適用は従来どおり未モデルであり、今回の修正で全ての追加効果を実装したとは扱わない。

## 検証

最小回帰テストは、表示値と基礎値の区別、通常倍率、強化時にダメージが増えないこと、Pen Nibと複数回使用、Artifact、Skillのカウンター、Powerの割引と消失、Second Windによる種類別の廃棄を確認する。

対象2モジュール792件が成功。Modは.NET 9で警告0・エラー0。既存候補N8の再生では、Mad Scienceの敵HP7件の差が消え、比較可能なHP425項目が一致した。4件のポーションはこの監査で等価アクションを再構成できず、143項目は比較不能なので、モデル全体の一致率とは呼ばない。

全830テストも成功した。CLIの`SLIMES_WEAK --simulations 500 --seed 0`を実行し、合法な候補手の探索が終了することを確認した。

## 実機検証の事前条件

- 分類: 正しさの修正。新しい戦略の採用比較ではない。
- 対象: 誤差を観測した開発用N8CQ4ZKP2W。未知の確認用seedには数えない。
- 比較元: 固定比較候補`20a8aee`のN8結果とtrace。修正版のcommit・ソース・ModのSHA-256は実行前manifestで固定する。
- 条件: v0.107.1、Ironclad、Ascension 0、100 simulations、全戦闘をエージェント、Act 3まで。userdata-pinを毎回復元する。
- 予定: `astra_goal_r9`で1 run、上限1800秒。中断時は全試行を残して原因を確認し、同条件・別tagで1回だけ再実行する。
- 確認項目: 新Bridgeの基礎値と全pileの種類・追加効果、合法行動と例外、比較可能なHP、最終結果。一度も使われなかったカードも記録する。
- 判定: 仕様・観測・回帰テスト・全テストで正しさを判断し、実走が悪化した場合も結果を残す。この1 seedで全体の踏破率向上は主張しない。
