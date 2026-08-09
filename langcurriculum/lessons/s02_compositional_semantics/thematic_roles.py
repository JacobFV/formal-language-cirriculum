"""Lesson 19: ``thematic_roles`` — agent vs patient independent of word order.

Compositional semantics and logical language.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Pred, Rec, Tok
from ...lesson import Lesson
from ..._support.base import NAMES
from ..._support.extra import _shuffled, verbs


def gen_thematic_roles(rng: random.Random):
    """Who did it and who had it done to them. Half the episodes are passive, so
    first-mentioned is the agent exactly half the time: surface position is
    uninformative and only the voice marking decides."""
    agent, patient = rng.sample(NAMES, 2)
    verb = rng.choice(verbs())
    passive = rng.random() < 0.5
    toks = [patient, "was", verb, "by", agent] if passive else [agent, verb, patient]
    role = rng.choice(["agent", "patient"])
    answer = agent if role == "agent" else patient
    obs = Rec(sentence=Lst([Tok(w) for w in toks]), query=Pred("role", Ident(role)))
    return (obs, _shuffled(rng, [agent, patient]), answer,
            {"voice": "passive" if passive else "active", "agent": agent,
             "patient": patient, "role": role})


class ThematicRoles(Lesson):
    """Agent vs patient independent of word order."""

    id = "thematic_roles"
    number = 19
    level = 22
    section = "ii"
    section_title = "compositional semantics and logical language"
    teaches = "agent vs patient independent of word order"
    capabilities = ()
    axes = {'grammar_complexity': 3, 'compositional_depth': 2, 'reasoning_depth': 2}

    generate = staticmethod(gen_thematic_roles)
