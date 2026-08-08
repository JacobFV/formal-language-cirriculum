"""The admission test a lesson has to pass before its numbers mean anything.

A lesson is only evidence if its floors are right. Two generator bugs in this
curriculum's history produced fake competence — object-id order correlated with
the answer, and referring expressions that did not uniquely refer — and both
would have shown up as an agent "solving" a lesson it had not. So every lesson
must demonstrate three things over a block of freshly generated episodes:

* **it generates** — no exceptions across the block;
* **it is deterministic** — the same seed gives the same episode, every time;
* **its floor is low** — a constant guesser (always answering the most common
  gold label) scores near chance, not near one.

That last check is what catches a lesson that has quietly become a coin whose
answer is "no" 90% of the time. The threshold is loose for binary lessons (0.60)
and tighter for lessons with a larger answer set (0.45), and a lesson that trips
it is re-measured over a larger block before being condemned, because a constant
guesser's score is itself a random variable and a fair generator will trip a
fixed threshold now and then.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, Sequence

from .lesson import Lesson
from .registry import all_lessons, get, resolve

__all__ = ["verify_lesson", "verify_all"]


def verify_lesson(lesson: Lesson | str, *, episodes: int = 200, seed0: int = 0) -> dict[str, Any]:
    """Generate episodes and check that the lesson measures what it claims to."""
    if isinstance(lesson, str):
        lesson = get(lesson)
    if lesson.status != "implemented":
        return {"lesson": lesson.id, "status": lesson.status, "ok": None, "note": lesson.note}
    answers: list[Any] = []
    vocabs: list[int] = []
    errors: list[str] = []
    determinism_ok = True
    for i in range(episodes):
        try:
            obs, vocab, ans, hidden = type(lesson).generate(random.Random(seed0 + i))
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
            continue
        if ans not in list(vocab):
            errors.append(f"answer {ans!r} not in the episode's answer set")
            continue
        answers.append(ans)
        vocabs.append(len(list(vocab)))
        if i < 5:                                    # same seed must give the same episode
            obs2, _, ans2, _ = type(lesson).generate(random.Random(seed0 + i))
            determinism_ok &= (str(obs) == str(obs2) and ans == ans2)
    if not answers:
        return {"lesson": lesson.id, "ok": False,
                "reason": errors[:2] or ["no episodes generated"]}

    counts = Counter(answers)
    n = len(answers)
    mean_vocab = sum(vocabs) / n
    uniform = sum(1.0 / v for v in vocabs) / n       # expected accuracy of a uniform guesser
    constant = counts.most_common(1)[0][1] / n       # accuracy of always guessing the mode
    limit = 0.60 if mean_vocab <= 2.2 else 0.45
    resampled = None
    if constant > limit and not errors:
        more: list[Any] = []
        for i in range(episodes * 4):
            try:
                _, _, a2, _ = type(lesson).generate(random.Random(seed0 + 100_000 + i))
                more.append(a2)
            except Exception:
                break
        if more:
            resampled = Counter(more).most_common(1)[0][1] / len(more)
            constant = resampled
    ok = (not errors) and determinism_ok and constant <= limit
    return {"lesson": lesson.id, "section": lesson.section, "level": lesson.level,
            "number": lesson.number, "episodes": n, "answer_set": round(mean_vocab, 1),
            "uniform": round(uniform, 3), "constant": round(constant, 3), "limit": limit,
            "deterministic": determinism_ok,
            "constant_resampled": (round(resampled, 3) if resampled is not None else None),
            "errors": errors[:2], "ok": bool(ok)}


def verify_all(lessons: str | Sequence[str] | None = None, *,
               episodes: int = 200) -> list[dict[str, Any]]:
    """Verify a selection of lessons, in curriculum order."""
    chosen = resolve(lessons) if lessons is not None else list(all_lessons().values())
    return [verify_lesson(l, episodes=episodes) for l in chosen]
