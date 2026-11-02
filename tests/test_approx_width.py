"""Sanity checks for approx_width_of() — NOT golden tests against Node (that's the whole
point: this is a documented approximation, see approx_width.py's module docstring).
These just check the approximation is self-consistent and not wildly off."""

from svg_diagram.approx_width import approx_width_of


def test_cjk_is_wider_than_average_latin_letter():
    assert approx_width_of("日", 16) > approx_width_of("a", 16)


def test_width_scales_linearly_with_size():
    assert approx_width_of("hello", 32) == approx_width_of("hello", 16) * 2


def test_bold_is_wider_than_regular():
    assert approx_width_of("hello", 16, weight=700) > approx_width_of("hello", 16, weight=400)


def test_mono_is_fixed_width_per_character():
    assert approx_width_of("ii", 16, font="mono") == approx_width_of("WW", 16, font="mono")


def test_sans_is_not_fixed_width_per_character():
    assert approx_width_of("ii", 16, font="sans") != approx_width_of("WW", 16, font="sans")


def test_empty_atom_has_zero_width():
    assert approx_width_of("", 16) == 0


def test_cjk_roughly_one_em():
    w = approx_width_of("日", 20)
    assert 18 <= w <= 22
