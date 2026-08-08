"""Lesson 8: ``parse_depth`` — structural decomposition.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Rec, Str
from ...lesson import Lesson
from ..._support.base import _balanced, _max_depth


def gen_parse_depth(rng: random.Random):
    """Recover a structural property of the hidden parse: nesting depth."""
    depth = rng.randint(1, 5)
    s = _balanced(rng, depth)
    obs = Rec(string=Str(s), query=Ident("max_depth"))
    return obs, list(range(0, 7)), _max_depth(s), {"string": s}


class ParseDepth(Lesson):
    """Structural decomposition."""

    id = "parse_depth"
    number = 8
    level = 8
    section = "i"
    section_title = "symbols, grounding, and elementary language"
    teaches = "structural decomposition"
    capabilities = ()
    axes = {'recursion_depth': 3, 'grammar_complexity': 3}

    generate = staticmethod(gen_parse_depth)
