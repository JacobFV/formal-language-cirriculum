"""Lesson 169: ``symbolic_generalist`` — held-out mixture of other lessons, none appearing verbatim.

Ultimate transfer and open-world capstones.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Pred, Rec
from ...lesson import Lesson
from ..._support.capstone import _OWN_IDS, _dedup, _shuffled


def gen_symbolic_generalist(rng: random.Random):
    """A held-out mixture: two *different* lessons from the registry are
    instantiated into one composite world, and the query names which of the two
    worlds it is about.

    The mixture is drawn at call time from the registry, minus this section's
    own lessons (which would recurse), so it automatically covers every lesson
    any other section contributes. No episode is verbatim a curriculum episode —
    the learner must first work out which half of the record the question is
    about, in a vocabulary that is the union of both halves' answers — while the
    ground truth stays the component lesson's exact answer.
    """
    from ...registry import all_lessons

    own = _OWN_IDS
    pool = sorted((l for l in all_lessons().values()
                   if l.status == "implemented" and l.id not in own), key=lambda l: l.id)
    if len(pool) < 2:                                 # pragma: no cover - registry empty
        raise RuntimeError("symbolic_generalist needs at least two other implemented lessons")

    picked = None
    for _ in range(20):
        a, b = rng.sample(pool, 2)
        try:
            obs_a, voc_a, ans_a, hid_a = a.generate(rng)
            obs_b, voc_b, ans_b, hid_b = b.generate(rng)
        except Exception:                             # a broken lesson must not break this one
            continue
        if ans_a not in list(voc_a) or ans_b not in list(voc_b):
            continue
        picked = (a, b, obs_a, list(voc_a), ans_a, hid_a, obs_b, list(voc_b), ans_b, hid_b)
        break
    if picked is None:                                # pragma: no cover
        raise RuntimeError("symbolic_generalist could not draw a usable mixture")
    a, b, obs_a, voc_a, ans_a, hid_a, obs_b, voc_b, ans_b, hid_b = picked

    first = rng.random() < 0.5
    left, right = (obs_a, obs_b) if first else (obs_b, obs_a)
    asked = rng.choice(["north", "south"])
    if asked == "north":
        answer = ans_a if first else ans_b
        source = a.id if first else b.id
    else:
        answer = ans_b if first else ans_a
        source = b.id if first else a.id
    obs = Rec(north=left, south=right, query=Pred("resolve_query_in", Ident(asked)))
    vocab = _shuffled(rng, _dedup(list(voc_a) + list(voc_b)))
    hidden = {"components": [a.id, b.id], "asked": asked, "source": source,
              "answer": answer, "levels": [a.level, b.level]}
    return obs, vocab, answer, hidden


class SymbolicGeneralist(Lesson):
    """Held-out mixture of other lessons, none appearing verbatim."""

    id = "symbolic_generalist"
    number = 169
    level = 169
    section = "xvii"
    section_title = "ultimate transfer and open-world capstones"
    teaches = "held-out mixture of other lessons, none appearing verbatim"
    capabilities = ('abstraction', 'metareasoning', 'open_ended_discovery')
    axes = {'lexical_novelty': 4, 'compositional_depth': 4, 'reasoning_depth': 4, 'world_complexity': 4, 'ambiguity': 3}

    generate = staticmethod(gen_symbolic_generalist)
