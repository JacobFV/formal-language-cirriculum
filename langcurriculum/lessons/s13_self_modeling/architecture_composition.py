"""Lesson 140: ``architecture_composition`` — compose typed modules into the cheapest pipeline.

Self-modeling and architecture adaptation.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Num, Pred, Rec
from ...lesson import Lesson
from ..._support.selfmodel import _labels, _paths, _rules, _shuffled


def gen_architecture_composition(rng: random.Random):
    """Compose typed modules into the cheapest pipeline, and name its first stage.

    Modules are typed converters over representation stages, and two of them skip
    a stage at a price. Cheapest is therefore a shortest-path computation rather
    than a per-layer minimum, and picking the cheapest first module greedily is
    frequently wrong.
    """
    types = ["raw", "parsed", "logical", "plan"]
    spec = [(0, 1), (0, 1), (1, 2), (1, 2), (2, 3), (2, 3), (0, 2), (1, 3)]
    paths = _paths(spec, 0, 3)
    for _ in range(80):
        costs = rng.sample(range(1, 40), len(spec))
        totals = sorted(((sum(costs[e] for e in p), p) for p in paths), key=lambda t: t[0])
        if totals[0][0] != totals[1][0]:
            break
    best = totals[0][1]

    ids = _labels(rng, "mod", len(spec))
    facts = [Pred("module", Ident(ids[e]), Ident(types[u]), Ident(types[v]), Num(costs[e]))
             for e, (u, v) in enumerate(spec)]
    obs = Rec(modules=Lst(_shuffled(rng, facts)),
              rules=_rules("a_pipeline_is_a_chain_of_modules_whose_output_type_matches_the_next_input_type",
                           "pipeline_cost_is_the_sum_of_its_module_costs"),
              query=Pred("first_module_of_cheapest_pipeline", Ident(types[0]), Ident(types[-1])))
    return (obs, _shuffled(rng, ids), ids[best[0]],
            {"cheapest": [ids[e] for e in best], "cost": totals[0][0], "margin": totals[1][0] - totals[0][0]})


class ArchitectureComposition(Lesson):
    """Compose typed modules into the cheapest pipeline."""

    id = "architecture_composition"
    number = 140
    level = 140
    section = "xiii"
    section_title = "self-modeling and architecture adaptation"
    teaches = "compose typed modules into the cheapest pipeline"
    capabilities = ('architecture_adaptation', 'planning', 'abstraction')
    axes = {'reasoning_depth': 4, 'compositional_depth': 4, 'world_complexity': 3}

    generate = staticmethod(gen_architecture_composition)
