"""Lesson 31: ``translation`` — two generated languages, different words and order.

Language as action.
"""

from __future__ import annotations

import itertools
import random
from typing import Mapping, Sequence

from ..._structure import Lst, Num, Pred, Rec, Str
from ...lesson import Lesson
from ..._support.semantics import _nonce_words, _shuffled


def gen_translation(rng: random.Random):
    """Two independently generated languages: different words *and* word order.

    Neither side is English. The parallel corpus is four sentences; the query
    sentence is an unseen combination, so the mapping has to be recovered as a
    concept-to-word lexicon plus a permutation, not as a phrase table.

    Kept only if identifiable: over every position-alignment the corpus admits,
    the query must translate to the same word. A corpus that leaves a source
    word unseen, or that cannot distinguish two alignments, is resampled rather
    than labelled arbitrarily.
    """
    for _ in range(200):
        subj = rng.sample(["s1", "s2"], 2)
        verb = rng.sample(["v1", "v2"], 2)
        obj = rng.sample(["o1", "o2"], 2)
        concepts = subj + verb + obj
        src = dict(zip(concepts, _nonce_words(rng, 6, 3)))
        tgt_words = _nonce_words(rng, 6, 4, avoid=list(src.values()))
        tgt = dict(zip(concepts, tgt_words))
        roles = ["S", "V", "O"]
        o1 = _shuffled(rng, roles)
        o2 = _shuffled(rng, roles)
        if o1 == o2:
            continue

        triples = [(s, v, o) for s in subj for v in verb for o in obj]
        rng.shuffle(triples)
        support, held = triples[:4], triples[4]

        def render(t: tuple[str, str, str], lexicon: Mapping[str, str],
                   order: Sequence[str]) -> list[str]:
            m = {"S": t[0], "V": t[1], "O": t[2]}
            return [lexicon[m[r]] for r in order]

        k = rng.randrange(3)
        answer = render(held, tgt, o2)[k]

        corpus = [(render(t, src, o1), render(t, tgt, o2)) for t in support]
        q_words = render(held, src, o1)
        seen = set()
        for perm in itertools.permutations(range(3)):      # source slot -> target slot
            word_map: dict[str, str] = {}
            if any(word_map.setdefault(s[i], t[perm[i]]) != t[perm[i]]
                   for s, t in corpus for i in range(3)):
                continue
            src_slot = perm.index(k)
            if q_words[src_slot] in word_map:
                seen.add(word_map[q_words[src_slot]])
        if seen != {answer}:
            continue
        break
    else:                                                  # pragma: no cover
        raise RuntimeError("no identifiable corpus")

    pairs = [Pred("pair", Str(" ".join(render(t, src, o1))), Str(" ".join(render(t, tgt, o2))))
             for t in support]
    obs = Rec(corpus=Lst(_shuffled(rng, pairs)),
              query=Pred("target_word_at", Str(" ".join(render(held, src, o1))), Num(k)))
    return obs, _shuffled(rng, tgt_words), answer, {"source_order": o1, "target_order": o2,
                                                    "held_out": list(held), "index": k}


class Translation(Lesson):
    """Two generated languages, different words and order."""

    id = "translation"
    number = 31
    level = 31
    section = "iii"
    section_title = "language as action"
    teaches = "two generated languages, different words and order"
    capabilities = ('ontology_learning', 'lexical_grounding', 'abstraction')
    axes = {'lexical_novelty': 4, 'grammar_complexity': 3, 'compositional_depth': 3}

    generate = staticmethod(gen_translation)
