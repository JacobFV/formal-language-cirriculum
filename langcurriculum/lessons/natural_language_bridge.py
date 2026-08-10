"""``natural_language_bridge`` — an English sentence to the symbolic structure it denotes.

Analogy, causality, planning, and programs.
"""

from __future__ import annotations

import random

from .._structure import Ident, Lst, Pred, Rec, Tok
from ..lesson import Lesson
from ..generators.base import COLORS, SHAPES
from ..generators.ontology import ENTITIES, REL_WORDS, _english, _label_options, _shuffled


def gen_natural_language_bridge(rng: random.Random):
    """Which symbolic structure does this English sentence denote?

    The sentence is *generated from* the structure, so the mapping is exact; the
    world is arranged so that neither colour nor shape alone is a definite
    description and both must be used to resolve a noun phrase to an id. Every
    distractor is rendered too and rejected unless it produces a different
    sentence — a distractor that says the same thing would make the episode
    unanswerable rather than hard.
    """
    for _ in range(200):
        ids = rng.sample(list(ENTITIES), 4)
        c1, c2 = rng.sample(COLORS, 2)
        s1, s2 = rng.sample(SHAPES, 2)
        combos = _shuffled(rng, [(c1, s1), (c1, s2), (c2, s1), (c2, s2)])
        world = {i: {"id": i, "color": c, "shape": s} for i, (c, s) in zip(ids, combos)}
        rels = rng.sample(list(REL_WORDS), 3)
        form = rng.choice(["rel", "not", "and"])
        a, b, c = rng.sample(ids, 3)
        if form == "rel":
            true = Pred(rels[0], Ident(a), Ident(b))
            cands = [Pred(rels[0], Ident(b), Ident(a)),
                     Pred(rels[1], Ident(a), Ident(b)),
                     Pred(rels[0], Ident(a), Ident(c))]
        elif form == "not":
            true = Pred("not", Pred(rels[0], Ident(a), Ident(b)))
            cands = [Pred(rels[0], Ident(a), Ident(b)),
                     Pred("not", Pred(rels[0], Ident(b), Ident(a))),
                     Pred("not", Pred(rels[1], Ident(a), Ident(b)))]
        else:
            true = Pred("and", Pred(rels[0], Ident(a), Ident(b)),
                        Pred(rels[1], Ident(a), Ident(c)))
            cands = [Pred("and", Pred(rels[0], Ident(a), Ident(c)),
                          Pred(rels[1], Ident(a), Ident(b))),
                     Pred("and", Pred(rels[1], Ident(a), Ident(b)),
                          Pred(rels[0], Ident(a), Ident(c))),
                     Pred("and", Pred(rels[0], Ident(a), Ident(b)),
                          Pred(rels[2], Ident(a), Ident(c)))]
        sentences = [" ".join(_english(world, s)) for s in [true, *cands]]
        if len(set(sentences)) == 4:
            break
    else:                                            # pragma: no cover - construction
        raise RuntimeError("natural_language_bridge: no episode")

    pairs, vocab, answer = _label_options(rng, true, cands)
    obs = Rec(
        world=Lst(_shuffled(rng, [Pred("obj", Ident(o["id"]), Ident(o["color"]), Ident(o["shape"]))
                                  for o in world.values()])),
        sentence=Lst([Tok(w) for w in sentences[0].split()]),
        candidates=Lst([Pred("candidate", Ident(lab), st) for lab, st in pairs]),
        query=Ident("denotation"),
    )
    hidden = {"form": form, "sentence": sentences[0], "structure": str(true), "answer": answer}
    return obs, vocab, answer, hidden


class NaturalLanguageBridge(Lesson):
    """An English sentence to the symbolic structure it denotes."""

    id = "natural_language_bridge"
    level = 60
    tags = ("analogy", "causality", "planning", "programs")
    teaches = "an English sentence to the symbolic structure it denotes"
    capabilities = ('grounding', 'parsing', 'surface_to_structure')
    axes = {'grammar_complexity': 3, 'compositional_depth': 3, 'ambiguity': 2, 'world_complexity': 2}

    generate = staticmethod(gen_natural_language_bridge)
