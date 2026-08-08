"""Lesson 1: ``symbol_grounding`` — denotation: symbol -> entity.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Pred
from ...lesson import Lesson
from ..._support.base import _scene, _scene_term


def gen_symbol_grounding(rng: random.Random):
    """Bind a symbol to the entity it denotes."""
    objs = _scene(rng, rng.randint(3, 5))
    tgt = rng.choice(objs)
    # make the description uniquely identifying
    while sum(1 for o in objs if o["color"] == tgt["color"] and o["shape"] == tgt["shape"]) > 1:
        objs = _scene(rng, rng.randint(3, 5))
        tgt = rng.choice(objs)
    q = Pred("which", Ident(tgt["color"]), Ident(tgt["shape"]))
    return _scene_term(objs, q), [o["id"] for o in objs], tgt["id"], {"target": tgt}


class SymbolGrounding(Lesson):
    """Denotation: symbol -> entity."""

    id = "symbol_grounding"
    number = 1
    level = 1
    section = "i"
    section_title = "symbols, grounding, and elementary language"
    teaches = "denotation: symbol -> entity"
    capabilities = ()
    axes = {'lexical_novelty': 0, 'world_complexity': 1, 'compositional_depth': 1}

    generate = staticmethod(gen_symbol_grounding)
