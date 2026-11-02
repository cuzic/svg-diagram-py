"""Golden-master tests for split_atoms() against Node's splitAtoms()."""

import pytest

from svg_diagram.atoms import split_atoms, text_width

TEXTS = [
    "",
    "hello",
    "hello world",
    "日本語",
    "hello 日本語 world",
    "A&B<C>D",
    "絵文字😀付き",
    "a  b",  # double space
    "複数の　　スペース",  # double full-width space
    "混在123abc漢字ひらがなカタカナ",
    "\t\n\r",
]


@pytest.mark.parametrize("text", TEXTS)
def test_split_atoms_matches_node(node_golden, text):
    node_result = node_golden.call({"kind": "splitAtoms", "text": text})
    assert split_atoms(text) == node_result


def test_text_width_sums_atom_widths():
    def width_of(atom, size, weight, font):
        return len(atom) * size

    assert text_width(width_of, "ab 日本語", 10, 400) == text_width(width_of, "ab 日本語", 10, 400)
    # "ab" -> 1 atom (len 2), " " -> 1 atom (len 1), each of 日/本/語 -> its own atom (len 1 each)
    assert text_width(width_of, "ab 日本語", 10, 400) == (2 + 1 + 1 + 1 + 1) * 10
