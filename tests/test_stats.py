"""Golden-master tests for stats.py against Node's lib/stats.ts (all exported, pure
functions of plain numbers — no layout/canvas involved, so these are tested directly
through the CLI's 'stats' dispatch rather than through a band)."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from svg_diagram import stats

XS = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
YS = [2.1, 0.9, 3.9, 1.2, 5.1, 8.8, 2.3, 5.9]


def test_sum_mean_sd(node_golden):
    assert stats.total(XS) == node_golden.call({"kind": "stats", "fn": "sum", "args": [XS]})
    assert stats.mean_of(XS) == node_golden.call({"kind": "stats", "fn": "meanOf", "args": [XS]})
    assert stats.sd_of(XS) == node_golden.call({"kind": "stats", "fn": "sdOf", "args": [XS]})


@pytest.mark.parametrize("p", [0, 0.25, 0.5, 0.75, 1])
def test_quantile(node_golden, p):
    s = sorted(XS)
    node_result = node_golden.call({"kind": "stats", "fn": "quantile", "args": [s, p]})
    assert stats.quantile(s, p) == pytest.approx(node_result)


def test_box_stats(node_golden):
    node_result = node_golden.call({"kind": "stats", "fn": "boxStats", "args": [XS]})
    assert asdict(stats.box_stats(XS)) == node_result


@pytest.mark.parametrize("df", [1, 5, 15, 30, 31, 100])
def test_t_critical_95(node_golden, df):
    node_result = node_golden.call({"kind": "stats", "fn": "tCritical95", "args": [df]})
    assert stats.t_critical_95(df) == pytest.approx(node_result)


@pytest.mark.parametrize("kind", ["ci", "sd", "se", "range", "none"])
def test_error_bar(node_golden, kind):
    node_result = node_golden.call({"kind": "stats", "fn": "errorBar", "args": [XS, kind]})
    py_result = stats.error_bar(XS, kind)
    assert (list(py_result) if py_result else None) == node_result


def test_kde(node_golden):
    grid = [i for i in range(11)]
    node_result = node_golden.call({"kind": "stats", "fn": "kde", "args": [XS, grid]})
    py_result = stats.kde(XS, grid)
    assert py_result["bw"] == pytest.approx(node_result["bw"])
    assert py_result["density"] == pytest.approx(node_result["density"])


def test_swarm_offsets(node_golden):
    at = [10, 12, 11, 50, 51, 90]
    node_result = node_golden.call({"kind": "stats", "fn": "swarmOffsets", "args": [at, 8, 100]})
    py_result = stats.swarm_offsets(at, 8, 100)
    assert py_result == pytest.approx(node_result)


def test_bin_counts_and_index(node_golden):
    edges = [0, 2, 4, 6, 8, 10]
    assert stats.bin_counts(XS, edges) == node_golden.call({"kind": "stats", "fn": "binCounts", "args": [XS, edges]})
    for v in XS:
        assert stats.bin_index(v, edges) == node_golden.call({"kind": "stats", "fn": "binIndex", "args": [v, edges]})


@pytest.mark.parametrize("order", [1, 2, 3])
def test_poly_fit(node_golden, order):
    probe = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    node_result = node_golden.call({"kind": "stats", "fn": "polyFit", "args": [XS, YS, order], "probeX": probe})
    r = stats.poly_fit(XS, YS, order)
    assert r.order == node_result["order"]
    assert r.coef == pytest.approx(node_result["coef"])
    assert r.r2 == pytest.approx(node_result["r2"])
    assert r.rss == pytest.approx(node_result["rss"])
    assert [r.at(x) for x in probe] == pytest.approx(node_result["atValues"])
    if node_result["halfValues"] is None:
        assert r.half is None
    else:
        assert [r.half(x) for x in probe] == pytest.approx(node_result["halfValues"])


def test_kde2d(node_golden):
    gx = [0, 2, 4, 6, 8]
    gy = [0, 2, 4, 6, 8]
    node_result = node_golden.call({"kind": "stats", "fn": "kde2d", "args": [XS, YS, gx, gy]})
    py_result = stats.kde2d(XS, YS, gx, gy)
    assert py_result["bwx"] == pytest.approx(node_result["bwx"])
    assert py_result["bwy"] == pytest.approx(node_result["bwy"])
    for py_row, node_row in zip(py_result["z"], node_result["z"], strict=True):
        assert py_row == pytest.approx(node_row)


def test_average_linkage_and_dendrogram_order(node_golden):
    data = [[1.0, 2.0], [1.5, 1.8], [5.0, 8.0], [8.0, 8.0], [1.0, 0.6], [9.0, 11.0]]
    node_result = node_golden.call({"kind": "stats", "fn": "averageLinkage", "args": [data]})
    merges = stats.average_linkage(data)
    assert [asdict(m) for m in merges] == node_result

    merges_for_node = [asdict(m) for m in merges]
    node_order = node_golden.call({"kind": "stats", "fn": "dendrogramOrder", "args": [merges_for_node, len(data)]})
    py_order = stats.dendrogram_order(merges, len(data))
    assert py_order["order"] == node_order["order"]
    assert py_order["pos"] == pytest.approx(node_order["pos"])


def test_lowess_fit(node_golden):
    probe = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    node_result = node_golden.call({"kind": "stats", "fn": "lowessFit", "args": [XS, YS], "probeX": probe})
    f = stats.lowess_fit(XS, YS)
    assert [f(x) for x in probe] == pytest.approx(node_result)
