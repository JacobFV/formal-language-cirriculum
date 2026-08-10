"""``symbol_discrimination`` — category boundaries.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random

from .._structure import Ident, Lst, Num, Pred, Rec
from ..lesson import Lesson


def gen_symbol_discrimination(rng: random.Random):
    """A hidden category boundary between near neighbours."""
    boundary = rng.randint(3, 7)
    v = rng.randint(0, 10)
    examples = [(k, "high" if k >= boundary else "low") for k in range(0, 11, 2) if k != v]
    rng.shuffle(examples)
    obs = Rec(examples=Lst([Pred("ex", Num(k), Ident(lab)) for k, lab in examples[:5]]),
              query=Pred("classify", Num(v)))
    return obs, ["low", "high"], ("high" if v >= boundary else "low"), {"boundary": boundary}


class SymbolDiscrimination(Lesson):
    """Category boundaries."""

    id = "symbol_discrimination"
    level = 3
    tags = ("symbols", "grounding", "elementary-language")
    teaches = "category boundaries"
    capabilities = ()
    axes = {'ambiguity': 1, 'reasoning_depth': 1}
    answers = ['low', 'high']

    generate = staticmethod(gen_symbol_discrimination)
