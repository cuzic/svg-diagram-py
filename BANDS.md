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
| sequence | ⬜ | ライフライン、メッセージ順で座標決定(閉形式の可能性) |
| wireframe / screens | ⬜ | 独自のflexレイアウトエンジン(844行) |
| chevron / funnel / cycle / venn / concentric / emblem / valueChain | ⬜ | renderFlowShape共通、形状ごとに閉形式幾何 |
| states(flowchartを含む) | ⬜ | |
| wordart | ⬜ | |
| classes (UML) | ⬜ | |

## Tier 3 — 専用図種(大規模)

| band | 状態 | 備考 |
|---|---|---|
| bowtie | ⬜ | |
| fta | ⬜ | Fault Tree Analysis |
| bpmn | ⬜ | レーン+フロー、大規模 |
| cause(CRT/FRT) | ⬜ | 最大規模。別計画で起票予定(交差削減・hop経路探索含む) |

## Tier 4 — chart系(種類が多い、使用頻度の高いものを優先)

| band/関数 | 状態 | 備考 |
|---|---|---|
| bars / stackedBars | ⬜ | |
| heatmap | ⬜ | |
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
