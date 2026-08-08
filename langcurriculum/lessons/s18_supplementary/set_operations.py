"""Supplementary lesson: ``set_operations`` — boolean algebra over property sets.

Supplementary syntax and semantics.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Pred, Rec
from ...lesson import Lesson
from ..._support.base import COLORS, SHAPES
from ..._support.extra import _formula, _obj_list, _objects, _shuffled


def gen_set_operations(rng: random.Random):
    """Conjunction, disjunction and negation over property sets. Formulas are
    sampled and then *rejected* unless they denote exactly one object, so the
    description is a definite one and the answer is unique."""
    objs = _objects(rng, 4)
    # colours and shapes each repeat once, so no single property is a definite
    # description and only a boolean combination picks out one object
    c1, c2 = rng.sample(COLORS, 2)
    s1, s2 = rng.sample(SHAPES, 2)
    for o, (c, s) in zip(objs, [(c1, s1), (c1, s2), (c2, s1), (c2, s2)]):
        o["color"], o["shape"] = c, s
    shown = _shuffled(rng, objs)
    for _ in range(80):
        sym, denoted, form = _formula(rng, objs)
        if len(denoted) == 1:
            break
    else:                                        # pragma: no cover - construction
        t = rng.choice(objs)
        sym = Pred("and", Pred("color", Ident(t["color"])), Pred("shape", Ident(t["shape"])))
        denoted, form = [t["id"]], "and"
    obs = Rec(scene=_obj_list(shown), query=Pred("select", sym))
    return (obs, _shuffled(rng, [o["id"] for o in objs]), denoted[0],
            {"form": form, "formula": str(sym), "denotes": denoted[0]})


class SetOperations(Lesson):
    """Boolean algebra over property sets."""

    id = "set_operations"
    number = None
    level = 26
    section = "supplementary"
    section_title = "supplementary syntax and semantics"
    teaches = "boolean algebra over property sets"
    capabilities = ()
    axes = {'compositional_depth': 4, 'reasoning_depth': 3, 'world_complexity': 2}

    generate = staticmethod(gen_set_operations)
