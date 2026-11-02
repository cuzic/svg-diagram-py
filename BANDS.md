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
| wireframe / screens | ⬜(保留) | lib/wireframe.ts(844行)+lib/wireframe-parts.ts(444行、installPartsによるノード種別拡張)の専用flexエンジン。他bandと共有されない一枚岩の大規模実装で、規模・構造ともTier 3(layered routing)に近い。したがってTier 2から外し、着手するなら別計画として起票するのが合理的(本セッションでは見送り、chart系を先に進める)。**再調査(emblem/quadrant/bowtieの「過大評価」パターンを疑って確認)でも同じ結論**: renderPrims(描画側)はlib/emit-tables.tsの30行程度で小さいが、レイアウト側のlayoutWireframe/layoutScreensはwf.col/row/card/btn/input/select/chip/tabs/appbar/seek/kv/stat/list/table/alert/map/video/heat/pointcloud/chart/image/dialog/toast+installPartsの拡張ノードという巨大な語彙を持つ専用flexエンジンで、過大評価ではなく正しくTier 3級。見送り継続 |
| swimlane | ⬜(見つかった抜け、未着手) | BANDS.mdにこれまで未掲載だった抜け(ADR 0048、サービスブループリント用)。lib/layout-handlers.tsの`layoutSwimlane`(非export、~60行)は`ctx.placeBoxLike`(テキスト自動折返し+高さ自動計算を行うNode側`LayoutCtx`カーソル型レイアウト基盤——row()/grid()等が共有する)に依存する。本移植の`box()`/`row()`/`grid()`はこの基盤を意図的に持たず、`height`を呼び出し側が明示する絶対座標APIなので、facet()と同じ「アーキテクチャ不一致」(新しい合成アーキテクチャが必要)に該当し、サイズの問題ではない。また`layoutSwimlane`は非exportのためlive golden testも不可(Node実機キャプチャ方式が必要)。対象外相当、着手するなら別途アーキテクチャ検討が前提 |
| chevron / funnel / cycle / venn / concentric / emblem / valueChain | ✅ | layoutFlowShape/renderFlowShapeともexport済み、live golden test(7形状全て)。emblemは再調査の結果、lib/emblem-shapes.ts(157行、13形状の輪郭幾何)がlib/flow-shapes.tsのlayoutEmblem()から直接呼ばれるだけの小さな依存で、既存のflow_shapes.py基盤(Texts/anchor/render_flow_shapeのpath+fill分岐)にそのまま乗ることが判明、「別途必要」は見積もり過大だった。`emblem_shapes.py`にemblemOutline/emblemHeight/emblemMaxHeightをフル移植(emblemClearance/flatOutlineは非公開のテスト専用ヘルパーのため対象外)、flow_shapes.pyにemblem_band()/_layout_emblem()を追加。live golden test一発通過(13形状全網羅・sub折返し・tone・gap/minSize・複数行ラップ・エラー経路)。render_flow_shape()の`n()`がPython組込みroundを使っていて.5の境界で不一致になる既存バグ(round1化し忘れ)をこのテストで検出・修正 |
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
| bpmn | ⬜(再調査済み、Tier3確定) | emblem/quadrant/bowtie/ftaと同じ「過大評価」パターンを疑って再調査したが、今回は**裏付けが取れた**: `lib/bpmn.ts`(313行)は`layered-route.ts`の`layeredAttempt`ではなく`lib/graph-layout.ts`の`layoutLayered`(サイクル除去・longest-path layering・ALAP/tighten・層folding・barycenter交差削減・座標割当を含む257行)を直接呼ぶ——wrapperを経由しない分軽いが、肝心の重いアルゴリズム自体は同じで未移植。加えて`lib/orthogonal-route.ts`(97行、routeClear)も未移植。合計650行超級の投資で、bowtie/ftaのような「既存基盤に乗るだけ」の軽量ケースではない。Tier 3確定を維持 |
| cause(CRT/FRT) | ⬜ | 最大規模。別計画で起票予定(交差削減・hop経路探索含む) |

**bowtie・fta は Tier 3 から外して移植済み(✅、下記参照)——当初の一括 Tier 3 分類は過大評価だった。bpmn は再調査したが今回は過大評価ではなく確定(上記参照)。states/classes/causeは`layeredAttempt`そのものに依存するため同様にTier 3確定。**

| band | 状態 | 備考 |
|---|---|---|
| bowtie | ✅ | 再調査の結果、Tier 3格上げは誤り(layeredAttempt/layered-route.ts への依存は無い)と判明。lib/bowtie.ts(142行)の`layoutBowtie`は固定レイアウト(「the flow runs left to right everywhere」、tree/layered layout不使用)で、依存は`lib/tree.ts`のmeasureNode/nodeRuns(mindmap/tree移植時にtree_text.pyへ既に移植済み)と`lib/fit-width.ts`のfitLayout(幅ナローイングのカスケードのみ——bowtie()は方向探索もfoldingも使わないため、使われる範囲だけをスコープして`bowtie.py`内にローカルport、tree.pyの同種スコープノートを参照)。`bowtie_band`/`layout_bowtie`/`render_bowtie`をフル移植、live golden test一発通過(hazardの有無・maxNodeW数値/'auto'/既定ナローイング・barrier複数行・fitLayoutが失敗する経路含む17件) |
| fta | ✅ | 再調査の結果、Tier 3対象外と判明し移植完了。`lib/fta.ts`(313行)は`lib/layered-route.ts`のlayeredAttemptに依存せず、使うのは`lib/graph-layout.ts`の`layoutTree`(tidy-tree、mindmap/tree移植時に既に移植済み)と`lib/fit-width.ts`のfitLayout(bowtieと同じスコープ——`noDir: true`かつ`alt`無しで方向探索なし、foldingもautoWidthも不使用。bowtie.pyのローカル版を`fit_width.py`として共有モジュールへ昇格)。`lib/fta-analysis.ts`(149行、minimalCutSets/singlePoints/topProbabilityという論理解析の純粋関数——MOCUS系の最小カットセット・Shannon展開による確率計算)を`fta_analysis.py`にフル移植。`ftaResolve`(検証+ref解決、~90行)/`layoutFta`/`gatePath`/`markPath`/`renderFta`をフル移植。live golden test一発通過(25件: OR/AND/vote/inhibit各gate・house事象・ref共有・cutSets単一故障点バッジ・quant確率ノート・quantPeriod・maxNodeW数値/'auto'/既定ナローイング)。`ftaIds()`/`ftaTexts()`は未移植(前者はconnect()事前検証用、後者はテキスト事前登録用——いずれも本移植の既存方針で不要) |

## Tier 4 — chart系(種類が多い、使用頻度の高いものを優先)

| band/関数 | 状態 | 備考 |
|---|---|---|
| bars | ✅ | layoutBars/renderBarsともexport済み、live golden test(horizontal/vertical/stack(bars自体のstack:trueオプション)/cumulative(パレート)/range/edges/lines/vlines/plotInset)。rangeBars()/pareto()/histogram()/scatter()の便利ラッパーは未移植(lib/qc.ts等の統計ヘルパーとplane()が別途必要、見送り) |
| stackedBars | ✅ | bars({stack:true})とは別のDSL関数(lib/charts-stacked.ts、layoutStacked/stackedBand)。Canvas基盤。live golden test(stacked/percent両モード) |
| heatmap | ✅ | layoutHeatmap/renderChartともexport済み、live golden test(min/max/levels/decimals/scale/rowHeader/corner/cellH/null cell)。`charts_base.py`にCanvas共有基盤を新設(他chart種別もこの上に乗る) |
| sankey | ✅ | layoutSankey/renderChartともexport済み、live golden test(複数レイヤー・barycenter並べ替え・align left/justify・tone/danger破線・リンクラベル配置)。ノードアイコンはicon registry未移植のため対象外(iconOfは常に0) |
| radar | ✅ | layoutRadar/renderChartともexport済み、live golden test(1-4系列・min/max/rings・fill・values表示・凡例の折返し)。候補リストの構築順(`[d,F1..F4]`を3回繰り返す、まとめて1回ではない)がNodeのflatMapの実際の挙動と異なっていたバグをgolden testで検出・修正 |
| treemap | ✅ | layoutTreemap/renderChartともexport済み、live golden test(squarified配置・反復重み補正・group/leaf・percent・strictエラー)。TreemapNodeオブジェクトをMapキーに使う箇所はPythonのid()による参照同一性で代替 |
| waterfall | ✅ | layoutWaterfall/layoutWaterfallH/renderChartともexport済み、live golden test(start/delta/subtotal/total・dir v/h・connectors・値ラベルの内外配置)。縦横ともライブgolden test一発通過 |
| mekko | ✅ | stackedBarsと同じlayoutStacked/stackedBand経由。Canvas基盤の上に乗るためbars/stackedBarsと合わせて移植済み |
| lines | ✅ | `plane()`(lib/plane.ts、standalone band "plane"、layoutPlane/renderPlaneをフルで移植——軸・目盛・stages・点の8方向自動ラベル配置・evolves矢印とクラッシュ検出・monotone/centripetal曲線フィッティング+ベジエサンプリング・寸法線)の上にlines()のエルゴノミックな層(linesOpts)を移植。live golden testで検証(カテゴリ軸・target線・ideal線・stages+evolves・smooth path(monotone/非monotone両方)・dims)。**既知のfloat差**: パスの矢印方向(および非monotoneのcentripetal曲線)が内部でhypot()を使うため、V8のMath.hypotとCPythonのmath.hypotが最後の1 ULPで不一致になることがある(render後の表示には影響なし、テストはtoleranceありの比較を使用) |
| burndown / burnup / strategyCanvas | ✅ | lines()のラッパー(burndownOpts/burnupOpts/strategyCanvasOpts)を移植。live golden testで検証 |
| tornado | ✅ | layoutTornado/renderChartともexport済み、live golden test(sort有無・lowTone/highTone・base線・凡例の行折返し)。live golden test一発通過 |
| butterfly | ✅ | layoutButterfly/renderChartともexport済み、live golden test(sort given/left/right・leftTone/rightTone・両側バー配置)。live golden test一発通過 |
| harvey | ✅ | layoutHarvey/renderChartともexport済み、live golden test(null未評価セル・corner・highlight列の枠・凡例の4分割円)。live golden test一発通過 |
| bubble | ✅ | layoutBubble/renderChartともexport済み、live golden test(軸の自動拡張ループ・バブル内/外ラベル配置・サイズ凡例・閾値線)。自動拡張ループを含めてlive golden test一発通過 |
| combo | ✅ | layoutCombo/renderChartともexport済み、live golden test(bar+line混在・左右2軸の目盛り間隔合わせ探索・stack・凡例の行折返し・anchors)。Canvas基盤の上のchart系はこれで一通り完了(bubble/butterfly/combo/harvey/heatmap/radar/sankey/stackedBars/mekko/tornado/treemap/waterfall) |
| pert / causalLoop / dependencyNetwork | ⬜(Tier 3相当) | 調査の結果、3つとも`semnet-common.ts`の`networkCanvas()`経由で`lib/layered-route.ts`(606行、交差削減+直交ルーティングの`layeredAttempt`)に依存することが判明。これは states/classes が依存する**同じ**layered routingエンジン(「重要な発見」節参照)。したがってchart系の軽量bandではなく、Tier 3の「layered routingエンジン」をまとめて移植する別計画でこそ扱うべき(一度移植すれば states/classes/bpmn/fta/cause と合わせて8 band種別に効く)。causalLoopはさらに`semnet-ring.ts`(83行、ring配置)+`semnet-interventions.ts`(79行)にも依存。本セッションでは見送り |
| catplot(boxplot/violinplot/stripplot/swarmplot/pointplot/barplot) | ✅ | lib/stats.ts(統計計算、純粋関数)を`stats.py`としてフル移植(quantile/boxStats/errorBar/kde/swarmOffsets/polyFit/kde2d/averageLinkage/dendrogramOrder/lowessFit、live golden test 27件)。lib/charts-cat.tsの`layoutCat`/`catBand`を`catplot.py`に移植、Canvas基盤の上に乗る。live golden test一発通過(7つのDSL関数すべて、kindの重ね合わせ・hue・dir h/v含む) |
| displot(histplot/kdeplot/ecdfplot/rugplot) | ✅ | lib/charts-dist.tsの`layoutDist`/`distBand`を`distplot.py`に移植(lib/qc.tsの`histogramBins`/`exact`は必要な分だけ`distplot.py`内に再実装、qc.ts自体は移植せず)。live golden test一発通過(5つのDSL関数すべて、kindの重ね合わせ・複数グループ・bins/bw/element: step含む) |
| multiplot(hist2d/jointplot/kde2d/pairplot) | ✅ | lib/charts-multi.tsの`layoutMulti`/`multiBand`を`multiplot.py`に移植(4分岐: kde2dの等高線=marching squares、hist2dのグリッド、jointplotの散布図+周辺ヒストグラム、pairplotの散布図行列)。distplot.pyの`_histogram_bins`を再利用。live golden test一発通過(kde2d/kde2d名前衝突のCLI側バグのみ修正) |
| regplot / residplot | ✅ | lib/charts-reg.tsの`layoutReg`/`regBand`を`regplot.py`に移植(polyFit/lowessFitの曲線+信頼区間帯、group別のtone/dash)。live golden test一発通過(order 1-3・stats・lowess・group・residplot全パターン) |
| clustermap | ✅ | lib/charts-cluster.tsの`layoutCluster`/`clusterBand`を`clustermap.py`に移植(averageLinkage/dendrogramOrderの木、行/列デンドログラムのpath描画はjs_numの手動変換が必要だった=js_num漏れの実例)。live golden test一発通過後、js_num漏れを1箇所自己修正 |
| facet | ⛔(対象外、再調査の結果) | 当初「row()/group()の組み合わせのみ、低リスク」と見積もったが、実際はNode側の`row()`/`group()`が宣言的なBand木(どのDiagramにも属さない純粋データ)を組み立てるのに対し、本移植の`Diagram.row()`/`.group()`はDiagramへの副作用を伴う絶対座標APIで、Box以外の任意band(chart系等)を子として持てる「コンテナband」という型自体がPython側に存在しない。facet()を忠実移植するには新しい合成アーキテクチャの設計が必要で、Nodeとのgolden比較も原理的に不可能(Python側だけの新規座標APIになるため)。低優先度の便利関数のためにこの投資をするのは不釣り合いと判断し、対象外とする(wireframe/screens・states/classes等の既存の見送り判断と同じ理由付け) |

**これでTier 4のchart系は実質完了**(pert/causalLoop/dependencyNetworkはTier 3格上げ、facetは対象外)。本セッションで移植: stats.ts(統計基盤)、catplot系(6関数)、displot系(5関数)、multiplot系(4関数)、regplot/residplot、clustermap。全てlive golden test一発通過(カテゴリ理解・ヘルパー再利用が徹底できていたため)。

## Tier 5 — 見送り候補

| band | 状態 | 理由 |
|---|---|---|
| math | ⛔ | MathJaxによるTeX組版、重い依存。stdlib-onlyの方針と衝突 |
| image | ⛔ | ファイルI/O・画像埋め込み、優先度低 |
| quadrant | ✅ | 再調査の結果、plane()/layered-routeへの依存は無く(atoms/wrap/layout_utilのみ)、「保留」の判断時点では未確認だった。lib/quadrant.tsの`quadrantBand`/`layoutQuadrant`(758行)+lib/emit-figures.tsの`renderQuadrant`(~45行)を`quadrant.py`にフル移植: 9プリセット(bcg/ge/ansoff/nineBox/impactEffort/risk/stakeholder/positioning/eisenhower)・アイテム配置の衝突回避探索(オフセット格子+行の拡張リトライ)・バブルサイズ凡例・移動矢印・自由形状リージョン・8方向ラベル配置。live golden test一発通過(19件: プリセット・カスタム軸・crosshair+regions・group>4のhollowマーカー・行拡張リトライ経路含む)。chart系とのピア依存は無く、独立モジュール |

## 非busy diagram種別(DSLレベルのエイリアス、band自体は上に含む)

- `flowchart()` → `states` band
- `mindmap()` → `tree` band
