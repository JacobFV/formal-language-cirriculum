"""Presentation is meant to change the surface and nothing else. That is testable."""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.presentation import ANSWER_FORMATS, Presentation

FORMATS = [f for f in sorted(ANSWER_FORMATS) if f != "open"]
SAMPLE = ["symbol_grounding", "unification", "quantification", "analogy", "negation"]


@pytest.mark.parametrize("lesson", SAMPLE)
@pytest.mark.parametrize("fmt", FORMATS)
def test_the_answer_never_moves_when_only_the_format_does(lesson, fmt):
    """The invariant the whole design rests on.

    A presentation may change what the prompt looks like and what the expected
    reply reads as. It must not change which option is correct, or the surface
    has stopped being a surface.
    """
    base = lc.get(lesson).example(3)
    other = lc.get(lesson).example(3, presentation=f"english/{fmt}")
    assert other.answer == base.answer
    assert other.choices == base.choices
    assert other.observation == base.observation
    assert other.instance_id == base.instance_id


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_produces_a_target_the_prompt_supports(fmt):
    ex = lc.get("symbol_grounding").example(1, presentation=f"english/{fmt}")
    assert ex.target
    if ANSWER_FORMATS[fmt].target == "label":
        assert ex.target in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        assert f"{ex.target}: {ex.answer}" in ex.prompt
    elif ANSWER_FORMATS[fmt].target == "statement":
        assert ex.target == ex.answer
    else:
        assert ex.target.endswith(ex.answer)


def test_the_options_are_always_in_the_prompt():
    """Replies are open-form, so the answer set has to be readable from the body."""
    for fmt in FORMATS:
        ex = lc.get("symbol_grounding").example(0, presentation=f"english/{fmt}")
        for choice in ex.choices:
            assert choice in ex.prompt, (fmt, choice)


def test_the_open_format_is_refused_where_it_would_hide_a_needed_vocabulary():
    with pytest.raises(ValueError, match="open_answerable"):
        lc.get("symbol_grounding").example(0, presentation="english/open")


def test_instance_id_is_shared_across_presentations_and_differs_across_seeds():
    """The join key that makes agreement measurable without a judge."""
    a = lc.get("unification").example(7, presentation="english/labelled_label")
    b = lc.get("unification").example(7, presentation="spanish/listed_bare")
    c = lc.get("unification").example(8)
    assert a.instance_id == b.instance_id
    assert a.instance_id != c.instance_id


def test_a_presentation_round_trips_through_its_key():
    p = Presentation(language="turkish", answer_format="labelled_both", surface="raster")
    assert Presentation.parse(p.key()) == p


def test_a_bare_language_code_still_means_that_language():
    assert Presentation.parse("swahili").language == "swahili"
    assert lc.get("unification").example(0, language="swahili").language == "swahili"


def test_an_unknown_format_is_refused_with_the_list():
    with pytest.raises(ValueError, match="inline_bare"):
        Presentation(answer_format="no_such_format")


def test_a_lettered_prompt_is_scored_on_letters():
    """An oracle answering with the letter must score 1.0, not 0."""
    lesson = lc.get("symbol_grounding")
    table = {ex.prompt: ex.target
             for ex in lesson.examples(6, presentation="english/labelled_label")}
    r = lc.evaluate_lesson(lambda p: table.get(p, ""), lesson, n=6,
                           presentation="english/labelled_label")
    assert r.accuracy == 1.0
