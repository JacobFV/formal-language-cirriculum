"""The floors themselves: a lesson whose floor is high measures nothing."""

from __future__ import annotations

import pytest

import langcurriculum as lc

IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]
IDS = [l.id for l in IMPLEMENTED]


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_every_lesson_passes_its_own_admission_test(lesson):
    r = lc.verify_lesson(lesson, episodes=120)
    assert r["ok"], r


def test_the_spec_lesson_is_reported_as_such_rather_than_failing():
    r = lc.verify_lesson("open_world_research_agent")
    assert r["ok"] is None and r["status"] == "spec" and r["note"]


def test_verify_all_covers_the_selection():
    rows = lc.verify_all("v", episodes=40)
    assert len(rows) == 7
    assert all(row["ok"] for row in rows)


def test_a_rigged_lesson_is_caught():
    """The check has to be able to fail, or it is not a check."""

    class AlwaysYes(lc.Lesson):
        id = "always_yes"
        teaches = "nothing at all"

        @staticmethod
        def generate(rng):
            from langcurriculum._structure import Ident, Rec
            return Rec(query=Ident("q")), ["yes", "no"], "yes", {}

    r = lc.verify_lesson(AlwaysYes(), episodes=100)
    assert r["ok"] is False
    assert r["constant"] == 1.0
