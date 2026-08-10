"""``open_ended_concept_discovery`` — invent the concept that carves the marked set.

Open-ended epistemology.
"""

from __future__ import annotations

import random

from .._structure import Ident, Lst, Pred, Rec
from ..lesson import Lesson
from ..generators.base import COLORS, SHAPES
from ..generators.selfmodel import SIZES, _labels, _rules, _shuffled


def gen_open_ended_concept_discovery(rng: random.Random):
    """Invent-a-concept, scored: which candidate concept best carves the marked set?

    A concept's worth is the number of marked items it covers minus the number of
    unmarked ones it drags in, so a concept that covers everything scores badly
    and a concept that covers one marked item scores little. Exactly one candidate
    maximizes it.
    """
    for _ in range(120):
        items = [{"id": f"i{i}", "color": rng.choice(COLORS[:3]), "shape": rng.choice(SHAPES[:3]),
                  "size": rng.choice(SIZES)} for i in range(8)]
        marked = {it["id"] for it in items if rng.random() < 0.45}
        cands = []
        for _c in range(4):
            attrs = rng.sample(["color", "shape", "size"], rng.randint(1, 2))
            cond = [(a, rng.choice({"color": COLORS[:3], "shape": SHAPES[:3], "size": SIZES}[a]))
                    for a in attrs]
            cands.append(cond)
        scores = []
        for cond in cands:
            cover = [it for it in items if all(it[a] == v for a, v in cond)]
            scores.append(sum(1 for it in cover if it["id"] in marked)
                          - sum(1 for it in cover if it["id"] not in marked))
        top = max(scores)
        if scores.count(top) == 1 and top > 0 and marked:
            break
    best = scores.index(top)

    ids = _labels(rng, "concept", 4)
    ifacts = [Pred("item", Ident(it["id"]), Ident(it["color"]), Ident(it["shape"]), Ident(it["size"]))
              for it in items]
    ifacts += [Pred("marked", Ident(i)) for i in sorted(marked)]
    cfacts = [Pred("concept_condition", Ident(ids[i]), Ident(a), Ident(v))
              for i in range(4) for a, v in cands[i]]
    obs = Rec(data=Lst(_shuffled(rng, ifacts)),
              candidates=Lst(_shuffled(rng, cfacts)),
              rules=_rules("an_item_falls_under_a_concept_iff_it_satisfies_every_condition_of_that_concept",
                           "concept_score_is_marked_items_covered_minus_unmarked_items_covered",
                           "choose_the_concept_of_highest_score"),
              query=Ident("best_concept"))
    return (obs, _shuffled(rng, ids), ids[best],
            {"scores": {ids[i]: scores[i] for i in range(4)}, "n_marked": len(marked)})


class OpenEndedConceptDiscovery(Lesson):
    """Invent the concept that carves the marked set."""

    id = "open_ended_concept_discovery"
    level = 146
    tags = ("open-ended-epistemology",)
    teaches = "invent the concept that carves the marked set"
    capabilities = ('open_ended_discovery', 'abstraction', 'ontology_learning')
    axes = {'reasoning_depth': 4, 'world_complexity': 3, 'compositional_depth': 3}

    generate = staticmethod(gen_open_ended_concept_discovery)
