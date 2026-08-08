"""Lesson 9: ``tree_to_sequence`` — realization from structure.

Symbols, grounding, and elementary language.
"""

from __future__ import annotations

import random
import string

from ..._structure import Ident, Rec
from ...lesson import Lesson
from ..._support.base import _mini_tree


def gen_tree_to_sequence(rng: random.Random):
    """Realize a symbolic tree as its surface form (here: its yield)."""
    depth = rng.randint(1, 3)
    tree, yield_ = _mini_tree(rng, depth)
    obs = Rec(tree=tree, query=Ident("first_leaf"))
    return obs, list(string.ascii_lowercase[:6]), yield_[0], {"yield": yield_}


class TreeToSequence(Lesson):
    """Realization from structure."""

    id = "tree_to_sequence"
    number = 9
    level = 9
    section = "i"
    section_title = "symbols, grounding, and elementary language"
    teaches = "realization from structure"
    capabilities = ()
    axes = {'recursion_depth': 2, 'compositional_depth': 2}

    generate = staticmethod(gen_tree_to_sequence)
