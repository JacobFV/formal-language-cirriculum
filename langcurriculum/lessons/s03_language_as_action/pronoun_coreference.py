"""Lesson 22: ``pronoun_coreference`` — resolving a pronoun to its one valid antecedent.

Language as action.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Pred, Rec, Tok
from ...lesson import Lesson
from ..._support.base import NAMES
from ..._support.extra import ADVERBS, GENDER, INTRANSITIVE, VERBS, _shuffled


def gen_pronoun_coreference(rng: random.Random):
    """Two entities, one pronoun, exactly one grammatically valid antecedent —
    the other entity is ruled out by gender, so the episode has a single correct
    reading. Filler material varies the distance to the antecedent."""
    fem = [n for n in NAMES if GENDER[n] == "f"]
    masc = [n for n in NAMES if GENDER[n] == "m"]
    she_ref, he_ref = rng.choice(fem), rng.choice(masc)
    first, second = (she_ref, he_ref) if rng.random() < 0.5 else (he_ref, she_ref)
    pron = rng.choice(["she", "he"])
    referent = she_ref if pron == "she" else he_ref
    filler = [rng.choice(ADVERBS) for _ in range(rng.randint(0, 2))]
    toks = [first, rng.choice(VERBS), second] + filler + ["then", pron, rng.choice(INTRANSITIVE)]
    obs = Rec(discourse=Lst([Tok(w) for w in toks]), query=Pred("refers_to", Ident(pron)))
    return (obs, _shuffled(rng, [she_ref, he_ref]), referent,
            {"pronoun": pron, "referent": referent,
             "distractor": he_ref if pron == "she" else she_ref,
             "distance": toks.index(pron) - toks.index(referent)})


class PronounCoreference(Lesson):
    """Resolving a pronoun to its one valid antecedent."""

    id = "pronoun_coreference"
    number = 22
    level = 23
    section = "iii"
    section_title = "language as action"
    teaches = "resolving a pronoun to its one valid antecedent"
    capabilities = ()
    axes = {'discourse_horizon': 3, 'ambiguity': 2, 'compositional_depth': 2}

    generate = staticmethod(gen_pronoun_coreference)
