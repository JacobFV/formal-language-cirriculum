"""Surfaces are transcodes. These tests hold them to carrying the same problem."""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.surfaces import (NATIVE_SURFACES, REPRODUCIBILITY,
                                     RENDERER_VERSIONS, SURFACES, surface_names,
                                     transcode, transcode_example)
from langcurriculum.surfaces.font import GLYPHS, HEIGHT, WIDTH, covers
from langcurriculum.surfaces.raster import png, render
from langcurriculum.surfaces.spoken import collapses, number_words, spoken_form

SAMPLE = ["symbol_grounding", "unification", "negation", "parse_depth"]

#: The surfaces that re-present the same string. A native surface is a different
#: kind of thing and gets its own tests further down.
TRANSCODES = [s for s in surface_names() if s not in NATIVE_SURFACES]

#: Surfaces whose text is the words as spoken rather than the prompt verbatim.
SPOKEN = {"spoken", "audio"}


@pytest.mark.parametrize("surface", TRANSCODES)
def test_a_transcode_is_deterministic(surface):
    """Same text, same options, same bytes — the claim the whole cache rests on."""
    text = "In the scene: o0 is a red cube at (4, 8).\nWhich object is red?"
    a = transcode(text, surface, target="o0", choices=("o0", "o1"))
    b = transcode(text, surface, target="o0", choices=("o0", "o1"))
    assert a.text == b.text
    assert [x.sha256 for x in a.assets] == [x.sha256 for x in b.assets]


@pytest.mark.parametrize("surface", TRANSCODES)
@pytest.mark.parametrize("lesson", SAMPLE)
def test_a_transcode_carries_the_same_underlying_text(surface, lesson):
    """A surface may re-present the string; it may not change the problem."""
    ex = lc.get(lesson).example(2)
    content = transcode_example(ex, surface)
    assert content.surface == surface
    if surface in SPOKEN:
        # read aloud, not copied: the written form is kept alongside so no
        # consumer of a dictated corpus has to transcribe it back
        assert content.text and content.text != ex.prompt
        assert content.meta["written"] == ex.prompt
    else:
        assert content.text == ex.prompt


@pytest.mark.parametrize("surface", surface_names())
def test_every_surface_states_what_it_guarantees(surface):
    assert RENDERER_VERSIONS[surface]
    assert REPRODUCIBILITY[surface]
    assert surface in SURFACES or surface in NATIVE_SURFACES


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
    frames = [a for a in content.assets if a.role == "frame"]
    assert len(frames) > 1
    digests = [a.sha256 for a in frames]
    assert len(set(digests)) == len(digests), "frames must not repeat"
    assert content.meta["frames"] == len(frames)


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


# ---------------------------------------------------------------- font coverage
def test_composition_covers_latin_europe_without_a_glyph_each():
    """An accented letter is a letter this font has, plus a mark."""
    from langcurriculum.surfaces.font import decompose, drawable
    for ch in "éàâñüößçğşıåøæœ":
        assert drawable(ch), ch
    base, above, below = decompose("é")
    assert base == "e" and above and not below
    base, above, below = decompose("ç")
    assert base == "c" and below and not above


def test_a_composed_letter_actually_draws_its_mark():
    from langcurriculum.surfaces.raster import render
    plain = render("n", columns=2, scale=1, padding=3).ascii_art()
    tilde = render("ñ", columns=2, scale=1, padding=3).ascii_art()
    assert tilde != plain
    assert tilde.count("#") > plain.count("#"), "the mark was not drawn"


def test_every_shipped_language_is_either_drawable_or_reported():
    """Coverage is measured against real episodes, never assumed."""
    from langcurriculum.surfaces.font import covers
    for code in ("english", "spanish", "turkish", "swahili", "english_synonym"):
        missing = set()
        for lid in SAMPLE:
            missing |= set(covers(lc.get(lid).example(0, language=code).prompt))
        assert not missing, f"{code} needs glyphs for {sorted(missing)}"


def test_cjk_is_declared_missing_rather_than_drawn_wrong():
    from langcurriculum.surfaces.font import covers
    assert covers("模式") == ("式", "模")


# ---------------------------------------------------------------- containers
def test_an_animation_is_a_real_apng_and_is_deterministic():
    from langcurriculum.surfaces.raster import apng, render
    pages = [render(t, columns=8, scale=1) for t in ("a", "ab", "abc")]
    data = apng(pages)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in data and b"fcTL" in data and b"fdAT" in data
    assert apng(pages) == data


def test_frames_of_different_sizes_are_refused():
    from langcurriculum.surfaces.raster import apng, render
    with pytest.raises(ValueError, match="same size"):
        apng([render("a", columns=8, scale=1), render("a", columns=20, scale=1)])


def test_the_video_surface_ships_a_container_beside_its_frames():
    ex = lc.get("unification").example(0)
    c = transcode_example(ex, "video", columns=40, scale=1)
    kinds = {a.mime for a in c.assets}
    assert kinds == {"image/apng", "image/png"}
    assert c.meta["container"].startswith("apng")


# ---------------------------------------------------------------- audio
def test_pronunciation_is_rule_based_and_covers_invented_words():
    from langcurriculum.surfaces.phonemes import pronounce_word
    assert pronounce_word("cube") == ("K", "Y", "UW", "B")
    assert pronounce_word("red") == ("R", "EH", "D")
    # a word no dictionary has still gets a pronunciation
    assert pronounce_word("blicket") == ("B", "L", "IH", "K", "EH", "T")
    assert pronounce_word("zzzqx"), "no word may come out silent"


def test_synthesis_is_deterministic_and_independent_of_the_global_rng():
    import random as _random
    from langcurriculum.surfaces.audio import say
    _random.seed(1)
    a = say("the red cube")
    _random.seed(999)
    b = say("the red cube")
    assert a == b, "the synthesizer read the global random state"


def test_a_waveform_is_a_valid_wav_of_plausible_length():
    from langcurriculum.surfaces.audio import duration_of, say
    data = say("the red cube is left of the green sphere.")
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    assert 1.0 < duration_of(data) < 12.0


def test_distinct_identifiers_do_not_become_the_same_sound():
    from langcurriculum.surfaces.audio import say
    assert say("o zero") != say("o one")


def test_the_audio_surface_reports_how_long_the_listening_is():
    ex = lc.get("symbol_grounding").example(0)
    c = transcode_example(ex, "audio")
    assert c.assets and c.assets[0].mime == "audio/wav"
    assert c.meta["seconds"] > 0
    assert c.meta["synthesis"].endswith("no model")


# ---------------------------------------------------------------- native scene
def test_the_scene_surface_draws_the_scene_not_the_sentence():
    from langcurriculum.surfaces import render_native, renders_natively
    lesson = lc.get("symbol_grounding")
    assert renders_natively(lesson)
    c = render_native(lesson, 0)
    assert c.surface == "scene" and c.meta["native"] is True
    assert c.assets[0].mime == "image/png"
    # the question travels as text beside the picture
    assert "Which object" in c.text


def test_a_drawn_scene_has_one_shape_per_object():
    from langcurriculum.surfaces.scene import objects
    lesson = lc.get("symbol_grounding")
    structured = lesson.structured(0)
    objs = objects(structured)
    assert objs and all(set(o) == {"id", "colour", "shape", "x", "y"} for o in objs)
    # and it matches what the text says
    text = lesson.example(0).observation
    for o in objs:
        assert o["id"] in text and o["colour"] in text and o["shape"] in text


def test_dropping_the_labels_is_reported_as_losing_the_answer():
    from langcurriculum.surfaces import render_native
    c = render_native(lc.get("symbol_grounding"), 0, labels=False)
    assert not c.fidelity.lossless
    assert any("cannot be answered" in n for n in c.fidelity.notes)


def test_a_lesson_with_no_scene_is_not_drawable_and_says_so():
    from langcurriculum.surfaces import render_native, renders_natively
    assert not renders_natively(lc.get("unification"))
    with pytest.raises(ValueError, match="no scene"):
        render_native(lc.get("unification"), 0)
    row = lc.verify.verify_surface("unification", "scene", episodes=2)
    assert row["ok"] is None and "nothing" in row["note"]


def test_a_native_surface_is_not_a_transcode():
    from langcurriculum.surfaces import NATIVE_SURFACES, render_native, transcode
    assert "scene" in NATIVE_SURFACES
    with pytest.raises(ValueError, match="unknown surface"):
        transcode("hi", "scene")
    with pytest.raises(ValueError, match="transcode, not a native"):
        render_native(lc.get("symbol_grounding"), 0, surface="raster")


def test_a_drawn_scene_is_deterministic():
    from langcurriculum.surfaces import render_native
    a = render_native(lc.get("quantification"), 5)
    b = render_native(lc.get("quantification"), 5)
    assert a.assets[0].sha256 == b.assets[0].sha256
