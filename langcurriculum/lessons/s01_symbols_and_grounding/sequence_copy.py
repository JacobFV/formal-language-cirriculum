"""Lesson 4: ``sequence_copy`` — sequence memory and indexing.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random
import string

from ..._structure import Lst, Num, Pred, Rec, Tok
from ...lesson import Lesson


def gen_sequence_copy(rng: random.Random):
    n = rng.randint(3, 6)
    seq = [rng.choice(string.ascii_lowercase[:6]) for _ in range(n)]
    k = rng.randrange(n)
    obs = Rec(sequence=Lst([Tok(s) for s in seq]), query=Pred("at", Num(k)))
    return obs, list(string.ascii_lowercase[:6]), seq[k], {"sequence": seq, "index": k}


class SequenceCopy(Lesson):
    """Sequence memory and indexing."""

    id = "sequence_copy"
    number = 4
    level = 4
    section = "i"
    section_title = "symbols, grounding, and elementary language"
    teaches = "sequence memory and indexing"
    capabilities = ()
    axes = {'discourse_horizon': 1}

    generate = staticmethod(gen_sequence_copy)
