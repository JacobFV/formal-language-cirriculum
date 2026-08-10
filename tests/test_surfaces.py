"""Surfaces are transcodes. These tests hold them to carrying the same problem."""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.surfaces import (REPRODUCIBILITY, RENDERER_VERSIONS, SURFACES,
                                     surface_names, transcode, transcode_example)
from langcurriculum.surfaces.font import GLYPHS, HEIGHT, WIDTH, covers
from langcurriculum.surfaces.raster import png, render
from langcurriculum.surfaces.spoken import collapses, number_words, spoken_form

SAMPLE = ["symbol_grounding", "unification", "negation", "parse_depth"]


@pytest.mark.parametrize("surface", surface_names())
def test_a_transcode_is_deterministic(surface):
    """Same text, same options, same bytes — the claim the whole cache rests on."""
    text = "In the scene: o0 is a red cube at (4, 8).\nWhich object is red?"
    a = transcode(text, surface, target="o0", choices=("o0", "o1"))
    b = transcode(text, surface, target="o0", choices=("o0", "o1"))
    assert a.text == b.text
    assert [x.sha256 for x in a.assets] == [x.sha256 for x in b.assets]


@pytest.mark.parametrize("surface", surface_names())
@pytest.mark.parametrize("lesson", SAMPLE)
def test_a_transcode_carries_the_same_underlying_text(surface, lesson):
    """A surface may re-present the string; it may not change the problem."""
    ex = lc.get(lesson).example(2)
    content = transcode_example(ex, surface)
    assert content.surface == surface
    if surface == "spoken":
        assert content.text and content.text != ex.prompt      # read aloud, not copied
    else:
        assert content.text == ex.prompt


@pytest.mark.parametrize("surface", surface_names())
def test_every_surface_states_what_it_guarantees(surface):
    assert RENDERER_VERSIONS[surface]
    assert REPRODUCIBILITY[surface]
    assert surface in SURFACES


def test_an_unknown_surface_is_refused_with_the_list():
    with pytest.raises(ValueError, match="raster"):
        transcode("hi", "hologram")


# ---------------------------------------------------------------- raster
def test_the_font_is_a_consistent_grid():
    for ch, bitmap in GLYPHS.items():
        assert len(bitmap) == HEIGHT, ch
        assert all(len(row) == WIDTH for row in bitmap), ch
        assert all(set(row) <= {"#", "."} for row in bitmap), ch


def test_the_font_covers_what_the_curriculum_actually_emits():
    """Measured, not assumed: render real episodes and check nothing is missing."""
    missing: set[str] = set()
    for lid in SAMPLE:
        for seed in range(5):
            missing |= set(covers(lc.get(lid).example(seed).prompt))
    assert not missing, f"the bundled font cannot draw {sorted(missing)}"


def test_a_rasterized_page_is_a_valid_png_of_the_right_size():
    page = render("hello", columns=10, scale=2, padding=4)
    data = png(page)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data.endswith(b"IEND\xaeB`\x82")
    import struct
    w, h = struct.unpack(">II", data[16:24])
    assert (w, h) == (page.width, page.height)


def test_glyphs_actually_land_on_the_page():
    """A blank page would be deterministic and useless."""
    page = render("A", columns=1, scale=1, padding=0, line_gap=0, letter_gap=0)
    assert page.ascii_art().replace(".", "").strip(), "nothing was drawn"
    assert page.ascii_art().splitlines()[3] == "#####"      # the crossbar of an A


def test_an_unknown_character_is_boxed_and_reported():
    content = transcode("ᚠ", "raster")
    assert content.fidelity.dropped == ("ᚠ",)
    assert not content.fidelity.lossless
    assert content.fidelity.notes


# ---------------------------------------------------------------- spoken
def test_numbers_are_read_as_numbers():
    assert number_words(0) == "zero"
    assert number_words(17) == "seventeen"
    assert number_words(42) == "forty two"
    assert number_words(305) == "three hundred five"
    assert number_words(-7) == "minus seven"


def test_punctuation_is_spoken_or_becomes_a_pause():
    said, _notes = spoken_form("f(x) = 3")
    assert "open paren" in said and "close paren" in said and "equals" in said


def test_identifiers_stay_distinguishable_when_read_aloud():
    """`o0` and `o1` must not become the same sound, or the lesson is unanswerable."""
    assert spoken_form("o0")[0] != spoken_form("o1")[0]
    assert not collapses(["o0", "o1", "o2", "o3"])


def test_options_that_sound_alike_are_reported_rather_than_rendered_anyway():
    clashes = collapses(["Cat", "cat", "dog"])
    assert clashes == (("Cat", "cat"),)
    content = transcode("pick one", "spoken", choices=("Cat", "cat"))
    assert not content.fidelity.lossless
    assert any("not answerable from audio" in n for n in content.fidelity.notes)


def test_case_loss_is_declared():
    content = transcode("Which One", "spoken", choices=("a", "b"))
    assert any("case" in n for n in content.fidelity.notes)


# ---------------------------------------------------------------- video
def test_a_reveal_produces_one_frame_per_line_and_they_differ():
    ex = lc.get("symbol_grounding").example(0)
    content = transcode_example(ex, "video", columns=40, scale=1)
    assert len(content.assets) > 1
    digests = [a.sha256 for a in content.assets]
    assert len(set(digests)) == len(digests), "frames must not repeat"
    assert content.meta["container"].startswith("none")


def test_scroll_declares_the_working_memory_demand_it_adds():
    content = transcode("a\nb\nc\nd\ne\nf\ng\nh", "video", mode="scroll", window=2,
                        columns=20, scale=1)
    assert any("working-memory" in n for n in content.fidelity.notes)


# ---------------------------------------------------------------- fidelity gate
@pytest.mark.parametrize("lesson", SAMPLE)
def test_verify_surface_agrees_with_the_transcode(lesson):
    row = lc.verify.verify_surface(lesson, "raster", episodes=4)
    assert row["ok"] is True
    assert row["lossy_episodes"] == 0
