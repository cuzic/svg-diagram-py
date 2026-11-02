# band 移植チェックリスト

svg-diagram の全band種別(`lib/emit-handlers.ts`のディスパッチ表、42種 + chart系のサブ種別多数)を重要度で分類し、移植状況を追跡する。
`flowchart()`は`states`band(StatesBand)を使う別名、`mindmap()`は`tree`bandを使う別名 —— 別エントリにしない。

凡例: ✅移植済み(golden test有) 🟡部分対応/近似 ⬜未着手 ⛔対象外(見送り)

## Tier 0 — コア(完了)

| band | 状態 | 備考 |
|---|---|---|
| box | ✅ | tag/stamp/step/frame/dim含む |
| connect | ✅ | ラベル・chip含む。strong/double は対象外 |
| caption | ✅ | |
| group | ✅ | |
| banner | ✅ | |
| legend | ✅ | swatch/line/AND/back/blocks。FTA/hex色/strong/doubleは対象外 |
| row | ✅ | 幅配分はNode.jsとバイト同一(純粋算術) |
| grid | ✅ | 同上 |
| raw | ✅ | |
| status | ✅ | |

## Tier 1 — 閉形式(auto-layout不要、着手中)

| band | 状態 | 備考 |
|---|---|---|
| cloud | ✅ | layoutCloudBand/renderCloudともexport済み、live golden test。**Tier 1完了** |
| pyramid | ✅ | 台形スタック、幾何はNode実機キャプチャとバイト同一を確認 |
| curve | ✅ | 点列配置もNode実機キャプチャとバイト同一を確認 |
| timeline | ✅ | layoutTimeline/renderTimelineともexport済み、live golden test。数値軸版(layoutNumeric)は見送り |
| gantt | ✅ | layoutGantt/renderGanttともexport済み、live golden test(依存矢印ルーティング・循環検出含む) |
| people | ✅ | layoutPeople/layoutDotsはexport済みなのでlive golden test、閉形式 |
| dots | ✅ | 同上 |

## Tier 2 — 中規模(auto-layoutあり、または複数分岐)

| band | 状態 | 備考 |
|---|---|---|
| mindmap / tree | ✅ | layoutTreeBand/renderTreeともexport済み、live golden test(fitLayoutの幅×方向探索も忠実に移植、org/list/brace/fishbone/timeline/radial/sides/curve全層対応)。band-node(tree({band}))は対象外 |
| table | ✅ | layoutTable/renderTableともexport済み、live golden test。アイコン付きセルは対象外 |
| sequence | ✅ | layoutSequence/renderSequenceともexport済み、live golden test(msg/self/note/divider全種別)。アクターアイコンは対象外 |
| wireframe / screens | ⬜(保留) | lib/wireframe.ts(844行)+lib/wireframe-parts.ts(444行、installPartsによるノード種別拡張)の専用flexエンジン。他bandと共有されない一枚岩の大規模実装で、規模・構造ともTier 3(layered routing)に近い。したがってTier 2から外し、着手するなら別計画として起票するのが合理的(本セッションでは見送り、chart系を先に進める) |
| chevron / funnel / cycle / venn / concentric / valueChain | ✅ | layoutFlowShape/renderFlowShapeともexport済み、live golden test(6形状全て) |
| emblem | ⬜ | lib/emblem-shapes.ts(~13形状の輪郭幾何+反復サイズ探索)が別途必要、見送り |
| wordart | ✅ | layoutWordArt/renderWordArtともexport済み、live golden test(horizontal/vertical/arc、全プリセット・gradient/plate/flip/rotate)。grapheme分割はIntl.Segmenter未再現(コードポイント単位の近似、approx_width.pyと同方針)、uid/gradient idはNode非再現(1枚のSVG内で一意なら十分、golden比較から除外) |

## 重要な発見: states/classes は Tier 3 相当(layeredAttempt依存)

調査の結果、`states`(flowchartを含む)と`classes`(UML)は`lib/layered-route.ts`の
`layeredAttempt`(layered graph routing — 交差削減・直交ルーティング・診断用
ラベル配置探索)に依存していることが判明した。これは`cause()`が使う
`lib/graph-layout.ts`の`layoutLayered`と同系統の重いエンジンで、cause()の
ために後回しにした「交差削減・hop経路探索」と同規模の投資が必要。
したがって states/classes は Tier 2 ではなく **Tier 3 に格上げし、
bpmn/fta/causeと合わせて「layered routing エンジン」をまとめて移植する
別計画で扱うのが合理的**(エンジン自体は一度移植すれば5 band種別
(states/flowchart/classes/bpmn/fta/cause)に効く)。

## Tier 3 — 専用図種(大規模、layered routing エンジン共有)

| band | 状態 | 備考 |
|---|---|---|
| states(flowchartを含む) | ⬜ | layeredAttempt依存。Tier2から格上げ |
| classes (UML) | ⬜ | layeredAttempt依存。Tier2から格上げ |
| bowtie | ⬜ | |
| fta | ⬜ | Fault Tree Analysis |
| bpmn | ⬜ | レーン+フロー、大規模 |
| cause(CRT/FRT) | ⬜ | 最大規模。別計画で起票予定(交差削減・hop経路探索含む) |

## Tier 4 — chart系(種類が多い、使用頻度の高いものを優先)

| band/関数 | 状態 | 備考 |
|---|---|---|
| bars / stackedBars | ✅ | layoutBars/renderBarsともexport済み、live golden test(horizontal/vertical/stack/cumulative(パレート)/range/edges/lines/vlines/plotInset)。rangeBars()/pareto()/histogram()/scatter()の便利ラッパーは未移植(lib/qc.ts等の統計ヘルパーとplane()が別途必要、見送り) |
| heatmap | ✅ | layoutHeatmap/renderChartともexport済み、live golden test(min/max/levels/decimals/scale/rowHeader/corner/cellH/null cell)。`charts_base.py`にCanvas共有基盤を新設(他chart種別もこの上に乗る) |
| sankey | ⬜ | |
| radar | ⬜ | |
| treemap | ⬜ | |
| waterfall | ⬜ | |
| lines | ⬜ | |
| burndown / burnup | ⬜ | |
| bubble / butterfly / combo / harvey / tornado / mekko | ⬜ | 優先度低 |
| pert / causalLoop / dependencyNetwork / strategyCanvas | ⬜ | 優先度低 |
| catplot / displot / clustermap / facet(seaborn系) | ⬜ | 優先度低 |

## Tier 5 — 見送り候補

| band | 状態 | 理由 |
|---|---|---|
| math | ⛔ | MathJaxによるTeX組版、重い依存。stdlib-onlyの方針と衝突 |
| image | ⛔ | ファイルI/O・画像埋め込み、優先度低 |
| quadrant | ⬜(保留) | 760行、plane()系とも絡む。Tier 2相当に見えるが規模的にTier 3寄り |

## 非busy diagram種別(DSLレベルのエイリアス、band自体は上に含む)

- `flowchart()` → `states` band
- `mindmap()` → `tree` band
