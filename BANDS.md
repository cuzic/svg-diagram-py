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
| wireframe / screens | ✅(coreのみ、2026-11) | lib/wireframe.ts(844行)のcoreエンジン(col/row/card + spacer/text/btn/input/select/chip/tabs/appbar/seek/kv/stat/list/table/alert/image/video/heat/pointcloud/chart/map、dialog/toast、state matrix、notes、new/changed凡例、skeleton)を layout_wireframe()/layout_screens() として、lib/emit-tables.tsのrenderPrims()(30行)を render_prims() として live golden test で移植。pointcloud()の散布用PRNG(32bit xorshift系)も32bit演算を明示的に再現してバイト同一。lib/wireframe-parts.ts(444行、installPartsによるstates/fusion/compare/region/robot/battery/signal/insight/breadcrumb/toggle/checkbox/radio/sliderの拡張)は対象外(監視・ロボット運用向けダッシュボードの専用追加機能で、既に大きいcoreとは独立)。map markerのid/shape/fov/heading(ロボットglyph、これもparts依存)はNotImplementedError。wf.*コンストラクタ糖衣・wireframeDefaults/shell・stateRow()もDSL層として未移植(呼び出し側がノード木を素のdictで組み立てる規約) |
| swimlane | ✅(2026-11、再評価の結果) | 当初は`ctx.placeBoxLike`依存を理由に facet 同様「アーキテクチャ不一致」として対象外にしていたが、再調査で訂正: `placeBoxLike`の計測部分(折返し・stamp/tag/icon・step バッジ)は id登録という副作用から分離できる(`lib/layout.ts`に`measureBoxLike`として抽出、Node本体にも反映済み)。これを使って`lib/swimlane.ts`の`layoutSwimlaneBand`(ctx無し、tree()/gantt()と同じ形でexport)を切り出し、`layout_swimlane_band`/`render_swimlane`/`render_box`としてlive golden testで移植した。対象外にしたのは他bandからのconnect()でステップを参照する機能(`opts.flows`・`opts.laneOrder`、どちらも共有アンカーレジストリが前提)のみ——facetの「コンテナbandという型がPython側に無い」問題とは異なり、swimlaneは本質的にアーキテクチャ不一致ではなかった |
| chevron / funnel / cycle / venn / concentric / emblem / valueChain | ✅ | layoutFlowShape/renderFlowShapeともexport済み、live golden test(7形状全て)。emblemは再調査の結果、lib/emblem-shapes.ts(157行、13形状の輪郭幾何)がlib/flow-shapes.tsのlayoutEmblem()から直接呼ばれるだけの小さな依存で、既存のflow_shapes.py基盤(Texts/anchor/render_flow_shapeのpath+fill分岐)にそのまま乗ることが判明、「別途必要」は見積もり過大だった。`emblem_shapes.py`にemblemOutline/emblemHeight/emblemMaxHeightをフル移植(emblemClearance/flatOutlineは非公開のテスト専用ヘルパーのため対象外)、flow_shapes.pyにemblem_band()/_layout_emblem()を追加。live golden test一発通過(13形状全網羅・sub折返し・tone・gap/minSize・複数行ラップ・エラー経路)。render_flow_shape()の`n()`がPython組込みroundを使っていて.5の境界で不一致になる既存バグ(round1化し忘れ)をこのテストで検出・修正 |
| wordart | ✅ | layoutWordArt/renderWordArtともexport済み、live golden test(horizontal/vertical/arc、全プリセット・gradient/plate/flip/rotate)。grapheme分割はIntl.Segmenter未再現(コードポイント単位の近似、approx_width.pyと同方針)、uid/gradient idはNode非再現(1枚のSVG内で一意なら十分、golden比較から除外) |

## layered routing エンジン(layeredAttempt)は移植完了——states/classes/pert/causalLoop/dependencyNetwork/causeの6つ全て完了

調査の結果、`states`(flowchartを含む)・`classes`(UML)・`cause`(CRT/FRT)・`pert`/`causalLoop`/`dependencyNetwork`(`semnet-common.ts`経由)は全て`lib/layered-route.ts`の
`layeredAttempt`(layered graph routing — 交差削減・直交ルーティング・AND矢印のレーン共有・並走回避・detour探索)に依存していると判明し、一度は「規模が大きすぎるため独立したサブプランとして十分な時間を確保してから着手する」と判断していた。
ユーザーの指示により専用のPlanフェーズ(Plan agentによる独立レビュー込み)を経て、`lib/layered-route.ts`本体(606行)を含むエンジン全体のフル移植が完了した(✅、下記参照)。
**これでエンジン自体は6つのband種別(states/flowchart/classes/bpmn/pert/causalLoop/dependencyNetwork、causeを含めれば7)に効く状態になった。** bpmn()はエンジンの一部(layoutLayered+routeClear)だけで足りたため既に完了済み(Tier 3から独立に解消)。続けてclassDiagram()(UML、下記参照)も完了——エンジンに加えて`lib/fit-width.ts`の本来の`fitLayout`/`planFit`(方向探索+幅ナローイング+折り返しの全探索、253行、classDiagram()は方向探索のみ使用)と`lib/fit-split.ts`(45行、高さ/幅に収まらない図の分割提案)もフル移植した。続けてstates/flowchart・pert・dependencyNetwork・causalLoopも完了(下記参照)。cause(CRT/FRT、`lib/toc.ts`、254行+groupOf/detour/apart/looseOf)のみ実装着手は別の投資として残る。

| 関数 | 状態 | 備考 |
|---|---|---|
| layoutLayered / breakCycles | ✅ | `lib/graph-layout.ts`の`layoutLayered`(257行、サイクル除去・longest-path layering・tighten/ALAP・層folding・barycenter交差削減・座標割当=relax/Brandes-Köpf)と`breakCycles`(DFSベースのサイクル検出、declared back edgeの妥当性検証含む)を`graph_layout.py`にフル移植。live golden test 34件一発通過 |
| routeClear | ✅ | `lib/orthogonal-route.ts`(97行、グリッド上のDijkstra探索による直交ルーティング)を`orthogonal_route.py`にフル移植。live golden test 10件一発通過。これとlayoutLayeredでbpmn()本体(313行)も移植できた |
| polyline-metrics | ✅ | `lib/polyline-metrics.ts`(82行、simplify/bendsOf/totalLength/crossingsOf/crossingsWith/scoreOf/runsTogether——折れ・交差・並走の判定を数える純粋関数、依存なし)を`polyline_metrics.py`にフル移植。live golden test 41件一発通過。check/lint側のedge-bends/edge-crossingsルール(本移植の対象外)でも共有される |
| route-apart | ✅ | `lib/route-apart.ts`(102行、moveApart——並走して1本の線に見えてしまう長い矢印を引き離すADR 0016 D14)を`route_apart.py`にフル移植。live golden test 4件一発通過 |
| route-search | ✅ | `lib/route-search.ts`(140行、headCrossings/searchRoute——箱の脇を通る格子上でのA*探索)を`route_search.py`にフル移植。手書きの二分ヒープをpush/pop含めて忠実に移植(タイブレークの挙動をPythonのheapqに委ねず再現)。live golden test 11件一発通過 |
| **layered-route(layeredAttempt本体)** | ✅ | `lib/layered-route.ts`(606行)を`layered_route.py`にフル移植。事前にPlan agentへ独立レビューを依頼し(ファイル全文の検証・フェーズ分割・翻訳の落とし穴の洗い出し・git blameによるADR系譜の確認)、承認済みプランに沿って実装。**フェーズ0**: `py/golden/emit_cli.ts`にdispatch caseを新設(従来0件)。place/groupOf/round(+layeredAttemptのみlooseOf)というコールバック引数はJSON越しに渡せないため、両サイドが同じ仕様(affine変換/`{edgeIndex:groupIndex}`/ノードid配列)から同じクロージャを組み立てる方式で解決(looseOfは唯一の実呼び出し元`toc.ts`のcause()専用のため対象外、`layeredAttempt`自身の既定`loose:[]`が実際に使う経路)。**フェーズ1**: `STUB`/`LANE`・`stubOf`/`laneStepOf`/`gapFor`/`elbows`/`corridorLoad`/`layoutWithLanes`(全てexport済みの小さな純粋関数)。`space=0.75`(`density:'compact'`)でJSの`Math.round`(半数+∞側)とPythonの組込み`round`(銀行丸め)が実際に分岐する値を明示的にテスト。**フェーズ2**: 非exportの`routeOnce`(約380行、ADR 0016のD3/D7/D11〜D14という8個以上の最適化パスが相互作用)を、exportされている`routeLayered`経由でのみブラックボックスとしてgolden test。Node側の1関数をPython側ではADR/パスごとに名前付きヘルパーに分解(翻訳の保守性のため、忠実性には影響しない)。line 152の非全順序なソート比較関数は`functools.cmp_to_key`で2引数のまま移植(タプルキーへの分解を避けた)。mutate-and-restoreの境界(D3の`align()`/`undo()`、spread再試行のロールバック)に非golden自己整合性assertionを追加。D3直線化・AND矢印のレーン共有・outer lane+laneHeads・detour探索が実際に発火する配置を手で確認した上でテスト(live golden test 18件)。**フェーズ3**: `layeredAttempt`本体(plain/BK候補の選択・D11共有・D12/D13 aside・D14 apart・far/near/low+laneHeadsの再試行)。4つの実呼び出し元(classes/states/toc(cause)/semnet-common)のオプション組み合わせを再現(live golden test 13件)。`cand.loose.length > plain.loose.length`の分岐(`looseOf`注入が無いと到達不能、toc.ts専用のため本スコープ外)は既知のギャップとして明示し、比較ロジック単体への非golden Pythonテストで代替。全フェーズでNode実機との一発またはテスト側の不備修正で通過(実装側のバグはゼロ、テストフィクスチャ側のnull/undefined取り扱いの不備を2件自己検出・修正) |

**bowtie・fta・bpmn・classes は Tier 3 から外して移植済み(✅)——当初の一括 Tier 3 分類は過大評価だった。states/pert/causalLoop/dependencyNetwork/causeもエンジンの上に完了、Tier 3は全band完了。**

| band | 状態 | 備考 |
|---|---|---|
| classes (UML) | ✅ | `lib/classes.ts`(176行)+`lib/emit-figures.ts`の`renderClasses`(~32行)を`classes.py`にフル移植。`layered_attempt`(dir 'down'/'right'の両方を試す、`transpose`/`tighten`/`portStep`)+`fit_width.py`の本来の`fitLayout`/`planFit`(本番初採用、`narrow:false`のためmaxNodeW探索は無し)の上に、クラスの計測(ヘッダ/属性/メソッドの3段構成)・継承/実装で親を先にする辺の反転・自己ループ(dir別に2種の幾何)・多重度/関係ラベルのチップ衝突回避配置を実装。`classesTexts()`は未移植(bpmnTexts/ftaTextsと同じ理由——テキスト事前登録、本移植では不要)。live golden test 44件一発通過(継承/コンポジション/集約/依存/開矢印の全関係種別・自己ループのdir right/down両方・dir autoでの方向選択・straighten:false・エラー経路5種)。これでstates/classes/causeの中で最初にband自体が完成した例になり、fit-width.ts本来のfitLayout/planFitが実運用で正しく動くことも実証された |
| states(flowchartを含む) | ✅ | `lib/states.ts`(stateDiagram()/flowchart()、同じband「states」をflavorで切り替え)+`lib/emit-figures.ts`の`renderStates`をstates.pyにフル移植。前提として`lib/flow-nodes.ts`(93行、decision用ダイヤモンドの最小サイズ探索・ダイヤモンド外周への矢印吸着・ダイヤモンドから真下に落ちる矢印の頂点吸着)・`lib/states-words.ts`(6行)・`lib/verify-base.ts`のstatesProblems()+必要な幾何ヘルパー(`density:'compact'`のフォールバック判定にレイアウト本体が実際に使うため、checkツール専用ではなくスコープ移植)も移植。`layered_attempt`(transpose/tighten/round(円は辺の途中で直線化しない)/returns:'all')+`fit_layout`/`plan_fit`の上に、円・ダイヤモンド・ピルの3形状計測・初期状態のダミーノード・自己ループ(dir別に2種の幾何)・decisionから真下に落ちる矢印の頂点吸着(ontoDiamond/vertexDrops)・遷移ラベルのチップ衝突回避配置(直線区間優先→経路上の点→オフセット)を実装。`statesTexts()`と状態の`icon`は未移植(bpmn.py/classes.pyと同じ理由)。live golden test: flow-nodes/states-words/verify-base 25件・states本体 32件、全て一発通過(render_states診断時に`js_num`漏れを1件自己検出・修正——クラスメンバーmap.pyで既に見つかっていたバグパターンの再発)。`Diagram.state_diagram()`/`Diagram.flowchart()`も追加。これでstates/classes/pert/causalLoop/dependencyNetworkの5つが完成、cause(CRT/FRT)のみ残る |
| cause(CRT/FRT/PRT/TT、causeTree()) | ✅ | `lib/toc.ts`のcauseTree()側(layoutCauseBand/layoutCauseBandOnce、423行中causeTree部分)+`lib/dsl/diagrams.ts`の非exportな`causeBand()`(DSLコンストラクタ、ported先はcause_band())+`lib/toc-analysis.ts`のreachCounts/coreDrivers(中核原因の到達数カウント)+`lib/emit-figures.ts`のrenderCauseをtoc.py/toc_analysis.pyにフル移植。前提の`lib/cause-clash.ts`(andClashes、ANDに入る矢印同士の交差/並走判定、28行)と`lib/cause-hop.ts`(causeCrossings、戻り矢印のhop迂回弧のスキップ判定、89行)もcause_clash.py/cause_hop.pyにフル移植(前のセッション単位)。`layered_attempt`のlooseOf(唯一の実呼び出し元がcause()——配線自体は既に通っていた、使うAND未成立判定`andEnds()`を新規実装)+`fit_layout`/`plan_fit`の上に、ADR 0019 D4の順序探索(交差した図を書かれた順の反転・回転6通り+seeded LCGによるシャッフル24通り+隣接swapで作り直し、lexLess採点で厳密に改善した時だけ採用)・ADR 0016 D11-D14(AND矢印のレーン共有/aside/apart、全てlayered_attempt側で既に実装済みのものを素通し)・ADR 0028のhop(戻り矢印が他の線を飛び越す迂回弧、`tree`指定時は既定`hop:'all'`)を実装。**前倒しで解消が必要だった依存**: `arrow_path()`の`cuts`引数(ADR 0028のhop描画、以前はNotImplementedErrorで止めていた)を`lib/emit-common.ts`の`cutPath()`として実装(cause()着手前に解消、hop:'all'が既定のtree指定figureで確実に踏むため)。`pdpc()`/`relationDiagram()`/`whyWhyTree()`/`transitionUnits()`/`prerequisiteTree()`/`transitionTree()`/`negativeBranchTree()`は未移植(causeBand()/causeTree()を別デフォルトで呼ぶだけの便利関数、または別の懸念=rca-rules.ts/toc-analysis.tsの別機能のため対象外、本移植の既存方針と同じ理由)。`mirrors`/`mirrorOf`/`rca`/`scope`/handle・anchorsのDSL糖衣も未移植(前2つはcheck専用でレイアウトに影響せず、scopeはこの移植全体で未実装、handle/anchorsは非enumerableプロパティでJSON出力に影響しないため)。live golden test: Node自身のtest/toc-fit.test.ts・test/cause-hop.test.tsが使う実在のストレステスト用トポロジー(AND交差の順序探索・D11レーン共有・D12/D13 aside・AND無しの交差のみ・hop true/false/'all'・density:'compact'・coreDriver・roleTags等)をそのまま流用し、layoutCauseBand/layoutCauseBandOnce/renderCauseのe2e比較で65件、ほぼ全て一発通過(最初の実装がNode実機と一致、オプションキーの命名規則(camelCase↔snake_case)というテスト側の不備のみ自己検出・修正)。`arrow_path(cuts=...)`は新規に4件のgolden test(単発hop/同じ辺に2つ/縦の辺/両端矢印)を追加。`Diagram.cause_tree()`も追加。これでTier 3は6band(states/flowchart/classes/bpmn/pert/causalLoop/dependencyNetwork/causeを含めれば8)全て完了 |

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
| pert | ✅ | `lib/semnet.ts`のresolvePert/pertAlt/layoutPert+`lib/semnet-dsl.ts`のpertBand()を移植。前提の`lib/semnet-common.ts`(111行、networkCanvas/arrow/nodeBox/placeEdgeLabel等——layered_attemptの上の共有Canvas基盤)と`lib/semnet-analysis.ts`のanalyzeCriticalPath()(CPM法: トポロジカル順序→ES/EF(前方)→LS/LF(後方)→slack→クリティカルパス)もフル移植(semnet_common.py/semnet_analysis.py)。既存の`charts.py`の`layout_chart`/`render_chart`ディスパッチャに'pert'kindを追加するだけで済み、Canvas基盤の再利用性が実証された。live golden test 20件(pert+dependency合算、下記参照)一発通過 |
| dependencyNetwork | ✅ | `lib/semnet.ts`のresolveDependency/dependencyAlt/layoutDependency+`lib/semnet-dsl.ts`のdependencyBand()を移植。pertと同じsemnet_common.py基盤を共有。ノード種別・辺種別の凡例(折返し行)・辺の太さ(weight)・ラベル配置(placeEdgeLabel、辺に沿う/脇に置く2段探索)を実装。`Diagram.pert()`/`Diagram.dependency_network()`も追加。エラー経路6種含めてlive golden test一発通過 |
| causalLoop | ✅ | `lib/semnet-analysis.ts`のanalyzeCausalLoops()(有向単純閉路の全列挙、開始ノードごとのDFS+`index[to]>=si`枝刈りで同じ閉路の重複発見を回避)を`semnet_analysis.py`に追加。`lib/semnet-ring.ts`(83行、ring配置——`layoutRing`の二分探索40回による弦の出入り点計算+半径を60から8px刻みで広げる再試行)を`semnet_ring.py`にフル移植。`lib/semnet-interventions.ts`(79行、`planInterventions`——介入ボックスの両端からの詰め直し+各矢印の直線/折れ線候補からの衝突回避選択)を`semnet_interventions.py`にフル移植。`lib/semnet-causal.ts`(145行、resolveCausal/causalAlt/causalTexts/layoutCausal+位置検証付き介入解決)を`semnet_causal.py`にフル移植。既存の`charts.py`の`layout_chart`/`render_chart`ディスパッチャに'causal'kindを追加、`semnet.py`の`semnet_texts()`の`causal`分岐をcausal_texts()呼び出しに差し替え(以前はNotImplementedError)。`Diagram.causal_loop()`も追加(他chart系と同じく`height`を露出——`layout:'ring'`がheightの下限を検証するため必要)。live golden test: analyzeCausalLoops/checkRing/bandInset/ringSide個別に加え、causalBand経由のlayoutChart/renderChart e2e 10件(layered既定/TB/delay+label/介入top/介入left(TB)/2つの独立loop(B1/R1)/ring既定/ring straighten:false/ringの自己ループ併存/ring介入top+bottom)、エラー経路12件以上、全て一発通過。**既知のfloat差**: ring配置の二分探索がmath.cos/sinを40回連鎖させるため、CPythonのlibmとV8のMath.cos/sinが最後の1 ULPで不一致になることがある(`segs`——未丸めの内部衝突判定専用データ、描画に出る`items`はjs_round経由で必ず一致——のみ、小数9桁までの比較に緩和。lines()バンドで既知の同種のfloat差と同じ性質) |
| catplot(boxplot/violinplot/stripplot/swarmplot/pointplot/barplot) | ✅ | lib/stats.ts(統計計算、純粋関数)を`stats.py`としてフル移植(quantile/boxStats/errorBar/kde/swarmOffsets/polyFit/kde2d/averageLinkage/dendrogramOrder/lowessFit、live golden test 27件)。lib/charts-cat.tsの`layoutCat`/`catBand`を`catplot.py`に移植、Canvas基盤の上に乗る。live golden test一発通過(7つのDSL関数すべて、kindの重ね合わせ・hue・dir h/v含む) |
| displot(histplot/kdeplot/ecdfplot/rugplot) | ✅ | lib/charts-dist.tsの`layoutDist`/`distBand`を`distplot.py`に移植(lib/qc.tsの`histogramBins`/`exact`は必要な分だけ`distplot.py`内に再実装、qc.ts自体は移植せず)。live golden test一発通過(5つのDSL関数すべて、kindの重ね合わせ・複数グループ・bins/bw/element: step含む) |
| multiplot(hist2d/jointplot/kde2d/pairplot) | ✅ | lib/charts-multi.tsの`layoutMulti`/`multiBand`を`multiplot.py`に移植(4分岐: kde2dの等高線=marching squares、hist2dのグリッド、jointplotの散布図+周辺ヒストグラム、pairplotの散布図行列)。distplot.pyの`_histogram_bins`を再利用。live golden test一発通過(kde2d/kde2d名前衝突のCLI側バグのみ修正) |
| regplot / residplot | ✅ | lib/charts-reg.tsの`layoutReg`/`regBand`を`regplot.py`に移植(polyFit/lowessFitの曲線+信頼区間帯、group別のtone/dash)。live golden test一発通過(order 1-3・stats・lowess・group・residplot全パターン) |
| clustermap | ✅ | lib/charts-cluster.tsの`layoutCluster`/`clusterBand`を`clustermap.py`に移植(averageLinkage/dendrogramOrderの木、行/列デンドログラムのpath描画はjs_numの手動変換が必要だった=js_num漏れの実例)。live golden test一発通過後、js_num漏れを1箇所自己修正 |
| facet | ⛔(対象外、再調査の結果) | 当初「row()/group()の組み合わせのみ、低リスク」と見積もったが、実際はNode側の`row()`/`group()`が宣言的なBand木(どのDiagramにも属さない純粋データ)を組み立てるのに対し、本移植の`Diagram.row()`/`.group()`はDiagramへの副作用を伴う絶対座標APIで、Box以外の任意band(chart系等)を子として持てる「コンテナband」という型自体がPython側に存在しない。facet()を忠実移植するには新しい合成アーキテクチャの設計が必要で、Nodeとのgolden比較も原理的に不可能(Python側だけの新規座標APIになるため)。低優先度の便利関数のためにこの投資をするのは不釣り合いと判断し、対象外とする(wireframe/screens・states/classes等の既存の見送り判断と同じ理由付け) |

**これでTier 4のchart系は完了**(pert/causalLoop/dependencyNetworkはTier 3格上げ、facetは対象外)。本セッションで移植: stats.ts(統計基盤)、catplot系(6関数)、displot系(5関数)、multiplot系(4関数)、regplot/residplot、clustermap、pert、dependencyNetwork、causalLoop(semnet-causal/ring/interventions一式)。全てlive golden test一発通過(カテゴリ理解・ヘルパー再利用が徹底できていたため)。

## Tier 5 — 見送り候補

| band | 状態 | 理由 |
|---|---|---|
| math | ⛔ | MathJaxによるTeX組版、重い依存。stdlib-onlyの方針と衝突 |
| image | ⛔ | ファイルI/O・画像埋め込み、優先度低 |
| quadrant | ✅ | 再調査の結果、plane()/layered-routeへの依存は無く(atoms/wrap/layout_utilのみ)、「保留」の判断時点では未確認だった。lib/quadrant.tsの`quadrantBand`/`layoutQuadrant`(758行)+lib/emit-figures.tsの`renderQuadrant`(~45行)を`quadrant.py`にフル移植: 9プリセット(bcg/ge/ansoff/nineBox/impactEffort/risk/stakeholder/positioning/eisenhower)・アイテム配置の衝突回避探索(オフセット格子+行の拡張リトライ)・バブルサイズ凡例・移動矢印・自由形状リージョン・8方向ラベル配置。live golden test一発通過(19件: プリセット・カスタム軸・crosshair+regions・group>4のhollowマーカー・行拡張リトライ経路含む)。chart系とのピア依存は無く、独立モジュール |

## 非busy diagram種別(DSLレベルのエイリアス、band自体は上に含む)

- `flowchart()` → `states` band
- `mindmap()` → `tree` band
