"""Lesson 20: ``instruction_following_micro`` — one command, one world update.

Language as action.
"""

from __future__ import annotations

import random

from ..._structure import Lst, Rec
from ...lesson import Lesson
from ..._support.base import COLORS
from ..._support.semantics import LOCATIONS, _act_sym, _apply, _instruction_query, _world, _world_facts


def gen_instruction_following_micro(rng: random.Random):
    """One command, one world update, then read back one state variable.

    The queried object is chosen independently of the command's argument, so
    half the episodes are answered by the initial state and half by the effect:
    copying the instruction's argument is wrong as often as it is right.
    """
    ids, st = _world(rng)
    init = {o: dict(v) for o, v in st.items()}
    verb = rng.choice(["paint", "move"])
    tgt = rng.choice(ids)
    if verb == "paint":
        val = rng.choice([c for c in COLORS if c != st[tgt]["color"]])
    else:
        val = rng.choice([l for l in LOCATIONS if l != st[tgt]["loc"]])
    act = (verb, tgt, val)
    _apply(st, act)

    query, vocab, answer, (slot, q) = _instruction_query(rng, ids, st)
    obs = Rec(world=_world_facts(ids, init),
              instruction=Lst([_act_sym("step", 0, act)]),
              query=query)
    return obs, vocab, answer, {"action": list(act), "queried": [q, slot],
                                "final": {o: dict(v) for o, v in st.items()}}


class InstructionFollowingMicro(Lesson):
    """One command, one world update."""

    id = "instruction_following_micro"
    number = 20
    level = 20
    section = "iii"
    section_title = "language as action"
    teaches = "one command, one world update"
    capabilities = ('planning', 'lexical_grounding')
    axes = {'world_complexity': 2, 'compositional_depth': 2, 'reasoning_depth': 2}

    generate = staticmethod(gen_instruction_following_micro)
