"""Lesson 11: ``unification`` — structural symbolic matching.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random
import string

from ..._structure import Ident, Pred, Rec
from ...lesson import Lesson
from ..._support.base import NAMES


def gen_unification(rng: random.Random):
    """Prolog-style term matching: parent(X,bob) vs parent(alice,bob) → X=alice."""
    a, b = rng.sample(NAMES, 2)
    var = rng.choice(list(string.ascii_uppercase[:5]))
    pos = rng.randrange(2)
    pattern = Pred("parent", Ident(var) if pos == 0 else Ident(a), Ident(b) if pos == 0 else Ident(var))
    fact = Pred("parent", Ident(a), Ident(b))
    obs = Rec(pattern=pattern, fact=fact, query=Pred("unify", Ident(var)))
    return obs, NAMES, (a if pos == 0 else b), {"var": var, "position": pos}


class Unification(Lesson):
    """Structural symbolic matching."""

    id = "unification"
    number = 11
    level = 11
    section = "i"
    section_title = "symbols, grounding, and elementary language"
    teaches = "structural symbolic matching"
    capabilities = ()
    axes = {'compositional_depth': 3, 'reasoning_depth': 3}
    answers = ['alice', 'bob', 'carol', 'dave', 'erin', 'frank']

    generate = staticmethod(gen_unification)
