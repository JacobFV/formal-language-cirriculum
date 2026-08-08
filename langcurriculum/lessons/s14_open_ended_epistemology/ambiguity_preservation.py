"""Lesson 155: ``ambiguity_preservation`` — how many readings the evidence leaves open.

Open-ended epistemology.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Pred, Rec
from ...lesson import Lesson
from ..._support.base import COLORS, SHAPES
from ..._support.selfmodel import _labels, _rules, _shuffled


def gen_ambiguity_preservation(rng: random.Random):
    """How many readings does the evidence leave open?

    A novel word has several senses licensed by the episode's lexicon, and the
    scene realizes some of them. Committing to one referent is exactly the error
    the lesson is built to catch, so the answer is the *size* of the admissible
    set — and it is greater than one most of the time.
    """
    k = rng.choice([1, 2, 3, 4])
    senses = rng.sample(COLORS, rng.randint(1, 3))
    outside = [c for c in COLORS if c not in senses]
    ids = _labels(rng, "o", 5)
    colors = [rng.choice(senses) for _ in range(k)] + [rng.choice(outside) for _ in range(5 - k)]
    objs = list(zip(ids, colors))
    word = "".join(rng.choice("kmtszlp") for _ in range(3))
    scene = [Pred("obj", Ident(i), Ident(c), Ident(rng.choice(SHAPES))) for i, c in objs]
    lex = [Pred("sense", Ident(word), Ident(c)) for c in senses]
    n = sum(1 for _i, c in objs if c in senses)
    assert n == k
    obs = Rec(lexicon=Lst(_shuffled(rng, lex)),
              scene=Lst(_shuffled(rng, scene)),
              rules=_rules("a_sense_fact_licenses_one_possible_meaning_of_the_word",
                           "a_reading_of_find_word_is_an_object_whose_colour_is_one_of_the_words_senses"),
              query=Pred("count_readings", Pred("find", Ident(word))))
    return (obs, _shuffled(rng, [1, 2, 3, 4]), k,
            {"senses": senses, "word": word, "readings": k})


class AmbiguityPreservation(Lesson):
    """How many readings the evidence leaves open."""

    id = "ambiguity_preservation"
    number = 155
    level = 155
    section = "xiv"
    section_title = "open-ended epistemology"
    teaches = "how many readings the evidence leaves open"
    capabilities = ('ambiguity_management', 'lexical_grounding')
    axes = {'ambiguity': 4, 'reasoning_depth': 3, 'world_complexity': 2}
    answers = [1, 2, 3, 4]

    generate = staticmethod(gen_ambiguity_preservation)
