"""The difficulty knob turns a lesson from one point into a curve.

The property that matters most is the negative one: with no difficulty asked
for, a lesson must generate exactly what it always did. A knob that moves the
unset case is not a knob, it is a silent change to every corpus already exported.
"""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.context import GenerationContext

WITH_KNOB = sorted(lid for lid, l in lc.all_lessons().items() if l.supports_difficulty())


def test_some_lessons_have_a_knob_and_the_rest_say_they_do_not():
    assert len(WITH_KNOB) >= 18
    for lid, lesson in lc.all_lessons().items():
        assert isinstance(lesson.supports_difficulty(), bool)
        assert lesson.info()["supports_difficulty"] == lesson.supports_difficulty()


@pytest.mark.parametrize("lid", WITH_KNOB)
def test_difficulty_changes_the_episode(lid):
    easy = [lc.get(lid).example(s, difficulty=0.0).prompt for s in range(8)]
    hard = [lc.get(lid).example(s, difficulty=1.0).prompt for s in range(8)]
    assert easy != hard, f"{lid} accepts a difficulty and ignores it"


@pytest.mark.parametrize("lid", WITH_KNOB)
def test_a_harder_episode_is_a_bigger_one(lid):
    """Difficulty scales structure, so the rendered episode should grow with it."""
    easy = sum(len(lc.get(lid).example(s, difficulty=0.0).observation) for s in range(12))
    hard = sum(len(lc.get(lid).example(s, difficulty=1.0).observation) for s in range(12))
    assert hard > easy, f"{lid} at difficulty 1.0 is not larger than at 0.0"


@pytest.mark.parametrize("lid", WITH_KNOB)
def test_difficulty_is_deterministic(lid):
    a = lc.get(lid).example(3, difficulty=0.7)
    b = lc.get(lid).example(3, difficulty=0.7)
    assert (a.prompt, a.answer) == (b.prompt, b.answer)


@pytest.mark.parametrize("lid", WITH_KNOB)
def test_a_scaled_lesson_still_answers_from_its_own_option_set(lid):
    """Scaling structure must not scale the answer out of the answer set."""
    for d in (0.0, 0.5, 1.0):
        for seed in range(6):
            ex = lc.get(lid).example(seed, difficulty=d)
            assert ex.answer in ex.choices, (lid, d, seed)


@pytest.mark.parametrize("lid", WITH_KNOB)
def test_the_floor_survives_being_scaled(lid):
    """A knob that makes a lesson trivially guessable has broken it."""
    row = lc.verify_lesson(lid, episodes=80, difficulty=1.0)
    assert row["ok"], row


def test_difficulty_is_part_of_the_problem_not_the_presentation():
    """Two difficulties are two problems, so they must not share an instance id."""
    a = lc.get("parse_depth").example(1, difficulty=0.0)
    b = lc.get("parse_depth").example(1, difficulty=1.0)
    assert a.instance_id != b.instance_id
    assert a.presentation == b.presentation


def test_an_out_of_range_difficulty_is_refused():
    with pytest.raises(ValueError):
        GenerationContext(difficulty=1.5)
    with pytest.raises(ValueError):
        lc.get("parse_depth").example(0, difficulty=-0.1)


def test_the_context_knobs_reproduce_their_defaults_when_unset():
    ctx = GenerationContext()
    assert ctx.at(3, 9, default=5) == 5
    assert ctx.span((3, 6), (8, 16)) == (3, 6)
    assert ctx.among(["a", "b", "c"]) == "a"
    assert not ctx.scaled


def test_the_context_knobs_interpolate_when_set():
    ctx = GenerationContext(difficulty=1.0)
    assert ctx.at(3, 9, default=5) == 9
    assert ctx.span((3, 6), (8, 16)) == (8, 16)
    assert ctx.among(["a", "b", "c"]) == "c"
    assert GenerationContext(difficulty=0.5).span((0, 10), (10, 20)) == (5, 15)
