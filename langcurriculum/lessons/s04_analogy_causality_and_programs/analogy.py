"""Lesson 41: ``analogy`` — a:b::c:? over a relational structure.

Analogy, causality, planning, and programs.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Pred, Rec
from ...lesson import Lesson
from ..._support.base import NAMES
from ..._support.extra import _shuffled


def gen_analogy(rng: random.Random):
    """``a : b :: c : ?`` over a relational structure. Two functional relations
    are laid over the same six entities and disagree on every entity, so exactly
    one of them explains the pair ``a:b`` and the answer is that relation applied
    to ``c``. Which relation was used is never named."""
    nodes = list(NAMES)
    for _ in range(200):
        p1 = _shuffled(rng, nodes)
        p2 = _shuffled(rng, nodes)
        if all(p1[i] != nodes[i] and p2[i] != nodes[i] and p1[i] != p2[i] for i in range(len(nodes))):
            break
    else:                                        # pragma: no cover - derangement
        p1 = nodes[1:] + nodes[:1]
        p2 = nodes[2:] + nodes[:2]
    r1, r2 = rng.sample(["follows", "outranks", "precedes", "mirrors"], 2)
    maps = {r1: dict(zip(nodes, p1)), r2: dict(zip(nodes, p2))}
    rel = rng.choice([r1, r2])
    a = rng.choice(nodes)
    b = maps[rel][a]
    c = rng.choice([x for x in nodes if x not in (a, b)])
    d = maps[rel][c]
    edges = [Pred(name, Ident(x), Ident(m[x])) for name, m in maps.items() for x in nodes]
    obs = Rec(graph=Lst(_shuffled(rng, edges)),
              query=Pred("analogy", Ident(a), Ident(b), Ident(c)))
    return (obs, _shuffled(rng, nodes), d,
            {"relation": rel, "a": a, "b": b, "c": c, "answer": d})


class Analogy(Lesson):
    """A:b::c:? over a relational structure."""

    id = "analogy"
    number = 41
    level = 29
    section = "iv"
    section_title = "analogy, causality, planning, and programs"
    teaches = "a:b::c:? over a relational structure"
    capabilities = ()
    axes = {'reasoning_depth': 4, 'compositional_depth': 3, 'world_complexity': 3}

    generate = staticmethod(gen_analogy)
