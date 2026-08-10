"""``variable_binding`` — variable identity vs token identity.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random
import string

from .._structure import Ident, Lst, Pred, Rec
from ..lesson import Lesson
from ..generators.base import NAMES


def gen_variable_binding(rng: random.Random):
    """Variable identity independent of token identity."""
    vs = rng.sample(list(string.ascii_uppercase[:5]), 2)
    vals = rng.sample(NAMES, 2)
    subst = [Pred("bind", Ident(vs[0]), Ident(vals[0])), Pred("bind", Ident(vs[1]), Ident(vals[1]))]
    rng.shuffle(subst)
    which = rng.randrange(2)
    obs = Rec(substitution=Lst(subst), query=Pred("value_of", Ident(vs[which])))
    return obs, NAMES, vals[which], {"bindings": dict(zip(vs, vals))}


class VariableBinding(Lesson):
    """Variable identity vs token identity."""

    id = "variable_binding"
    level = 10
    tags = ("symbols", "grounding", "elementary-language")
    teaches = "variable identity vs token identity"
    capabilities = ()
    axes = {'compositional_depth': 2, 'reasoning_depth': 2}
    answers = ['alice', 'bob', 'carol', 'dave', 'erin', 'frank']

    generate = staticmethod(gen_variable_binding)
