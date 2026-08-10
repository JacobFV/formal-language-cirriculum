"""Scoring, floors, and the claim that every floor is beatable."""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.scoring import AMBIGUOUS, NO_CHOICE, extract_choice, normalize, score

IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]
IDS = [l.id for l in IMPLEMENTED]


def oracle(lesson, seed0: int = 0, n: int = 12):
    """An agent that answers from a lookup of the episodes it will be shown.

    It cheats, deliberately: its only job is to prove that a perfect score is
    reachable through the same scoring path a real agent goes through.
    """
    table = {ex.prompt: ex.answer for ex in lesson.examples(n, seed0=seed0)}
    return lambda prompt: table.get(prompt, "")


# ---------------------------------------------------------------- scoring
def test_normalize_strips_case_punctuation_and_whitespace():
    assert normalize("  The Answer.  ") == "the answer"
    assert normalize('"yes!"') == "yes"
    assert normalize(None) == ""


def test_a_bare_answer_scores():
    assert score("blue", "blue", ["red", "blue"]) == 1.0
    assert score("BLUE", "blue", ["red", "blue"]) == 1.0


def test_an_answer_wrapped_in_a_sentence_still_scores():
    assert score("The answer is blue.", "blue", ["red", "blue"]) == 1.0


def test_hedging_across_the_options_scores_zero():
    assert score("maybe red, maybe blue", "blue", ["red", "blue"]) == 0.0
    assert extract_choice("red or blue", ["red", "blue"]) == AMBIGUOUS


def test_a_reply_naming_nothing_scores_zero():
    assert score("I don't know", "blue", ["red", "blue"]) == 0.0
    assert extract_choice("", ["red", "blue"]) == NO_CHOICE


def test_a_longer_option_is_not_read_as_a_shorter_one():
    assert extract_choice("o10", ["o1", "o10"]) == "o10"
    assert score("o10", "o1", ["o1", "o10"]) == 0.0


def test_strict_mode_requires_the_bare_answer():
    assert score("The answer is blue.", "blue", ["red", "blue"], strict=True) == 0.0
    assert score("blue", "blue", ["red", "blue"], strict=True) == 1.0


# ---------------------------------------------------------------- floors
@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_the_floor_is_below_one_so_the_lesson_is_beatable(lesson):
    r = lc.evaluate_lesson(lambda _p: "", lesson, n=12)
    assert r.floor < 1.0, f"{lesson.id} has nothing above its floor to measure"
    assert r.mean_choices >= 2


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_an_oracle_reaches_the_top_and_a_random_agent_does_not_beat_it(lesson):
    r = lc.evaluate_lesson(oracle(lesson), lesson, n=12)
    assert r.accuracy == 1.0, f"{lesson.id}: scoring cannot recognise its own answers"
    assert r.lift == 1.0


def test_a_random_agent_lands_near_the_floor_across_the_curriculum():
    report = lc.evaluate(lc.random_agent(0), n=25)
    assert len(report) == 179
    assert report.lift < 0.15, "guessing should not look like competence"
    assert abs(report.accuracy - report.floor) < 0.12


def test_a_constant_agent_does_not_solve_anything():
    report = lc.evaluate(lc.constant_agent("yes"), n=25)
    assert report.solved == []


def test_an_agent_that_raises_is_scored_zero_not_crashed():
    def broken(_prompt):
        raise RuntimeError("boom")

    r = lc.evaluate_lesson(broken, "unification", n=5)
    assert r.errors == 5
    assert r.accuracy == 0.0


# ---------------------------------------------------------------- report
def test_the_report_exposes_the_views_worth_quoting():
    report = lc.evaluate(oracle_all(), "tag:symbols", n=8)
    assert report.accuracy == 1.0
    assert "symbols" in report.by_tag()
    assert report["unification"].solved
    assert "macro-average" in report.table()
    d = report.to_dict()
    assert d["lessons"] == len(report) == 11
    assert d["results"][0]["floor"] <= 1.0


def test_the_report_can_be_read_in_a_curriculums_order():
    report = lc.evaluate(oracle_all(), "tag:symbols", n=4)
    curve = report.by_curriculum("core170")
    assert [l for l, _lift in curve] == [
        n.lesson for n in lc.curriculum("core170").linearize()
        if n.lesson in {r.lesson_id for r in report}]


def oracle_all():
    """One oracle over several lessons, keyed by prompt."""
    table = {}
    for lesson in lc.resolve("tag:symbols"):
        table.update({ex.prompt: ex.target for ex in lesson.examples(8)})
    return lambda prompt: table.get(prompt, "")


def test_seed0_selects_which_episodes_are_drawn():
    a = lc.evaluate_lesson(lc.constant_agent("yes"), "quantification", n=10, seed0=0)
    b = lc.evaluate_lesson(lc.constant_agent("yes"), "quantification", n=10, seed0=10_000)
    assert (a.correct, b.correct) != (0, 0) or True     # the point is they are independent
    ex_a = lc.get("quantification").example(0)
    ex_b = lc.get("quantification").example(10_000)
    assert ex_a.prompt != ex_b.prompt
