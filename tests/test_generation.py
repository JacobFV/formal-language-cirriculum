"""Every lesson generates, and generates the same thing twice."""

from __future__ import annotations

import json
import random

import pytest

import langcurriculum as lc
from langcurriculum._structure import Term
from langcurriculum.languages import language_codes

IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]
IDS = [l.id for l in IMPLEMENTED]


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_every_lesson_generates_a_well_formed_example(lesson):
    for seed in (0, 1, 7, 12345):
        ex = lesson.example(seed)
        assert ex.lesson_id == lesson.id
        assert ex.seed == seed
        assert isinstance(ex.prompt, str) and ex.prompt.strip()
        assert isinstance(ex.observation, str) and ex.observation.strip()
        assert ex.observation in ex.prompt
        assert len(ex.choices) >= 2, "an episode with fewer than two answers grades nothing"
        assert ex.answer in ex.choices, "the gold answer must be one of the choices"
        assert len(set(ex.choices)) == len(ex.choices), "duplicate choices"


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_the_same_seed_gives_the_same_episode(lesson):
    for seed in (0, 3, 99):
        a = lesson.example(seed)
        b = lesson.example(seed)
        assert a == b


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_different_seeds_give_different_worlds(lesson):
    """Not every pair need differ, but a block of 40 must not collapse to one."""
    prompts = {lesson.example(s).prompt for s in range(40)}
    assert len(prompts) > 1, f"{lesson.id} generates a constant episode"


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_generation_is_independent_of_global_random_state(lesson):
    random.seed(12345)
    a = lesson.example(4)
    random.seed(999)
    [random.random() for _ in range(50)]
    b = lesson.example(4)
    assert a == b


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_metadata_is_plain_json(lesson):
    ex = lesson.example(2)
    json.dumps(ex.to_dict())          # raises if anything is not plain data


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_every_language_picks_out_the_same_option(lesson):
    """A language changes the words, never which option is correct.

    The answer *string* differs once the options are translated — that is the
    point of translating them — so the invariant is positional: the same option
    of the same episode is right in every language.
    """
    indices = set()
    sizes = set()
    for code in language_codes():
        ex = lesson.example(5, language=code)
        assert ex.language == code
        assert ex.observation.strip()
        assert ex.answer in ex.choices
        indices.add(ex.choices.index(ex.answer))
        sizes.add(len(ex.choices))
    assert len(indices) == 1, f"{lesson.id}: the correct option moved between languages"
    assert len(sizes) == 1, f"{lesson.id}: the answer set changed size between languages"


def test_no_public_value_is_ever_an_internal_term():
    """The API promise: plain text and plain data, never the internal nodes."""
    for lesson in IMPLEMENTED[:60]:
        ex = lesson.example(1)
        payload = ex.to_dict()
        assert not _contains_term(payload), lesson.id
        assert not _contains_term(lesson.info()), lesson.id
        assert not _contains_term(lesson.structured(1)), lesson.id


def _contains_term(x) -> bool:
    if isinstance(x, Term):
        return True
    if isinstance(x, dict):
        return any(_contains_term(k) or _contains_term(v) for k, v in x.items())
    if isinstance(x, (list, tuple, set)):
        return any(_contains_term(i) for i in x)
    return False


def test_the_spec_lesson_refuses_rather_than_pretending():
    lesson = lc.get("open_world_research_agent")
    assert lesson.status == "spec"
    with pytest.raises(lc.LessonNotImplemented):
        lesson.example(0)


def test_an_unknown_language_is_rejected():
    with pytest.raises(ValueError):
        lc.get("unification").example(0, language="klingon")
