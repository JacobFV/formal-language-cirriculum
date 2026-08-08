"""Lesson 142: ``external_memory_design`` — index a symbolic store for its retrieval workload.

Self-modeling and architecture adaptation.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Num, Pred, Rec
from ...lesson import Lesson
from ..._support.selfmodel import _labels, _rules, _shuffled


def gen_external_memory_design(rng: random.Random):
    """Which index to build over a symbolic store, given the retrieval workload.

    An unindexed lookup scans; an index makes its own fields cheap and everything
    else unchanged; a composite index costs more to build but covers two fields.
    Exactly one design minimizes the total, and it is not always the one with the
    smallest build cost or the widest coverage.
    """
    fields = _labels(rng, "field", 4)
    counts = [rng.randint(1, 12) for _ in range(4)]
    scan = rng.randint(6, 16)
    ids = _labels(rng, "design", 5)
    for _ in range(80):
        designs = []
        for i in range(5):
            cover = sorted(rng.sample(range(4), 2 if i == 0 else 1))
            designs.append((cover, rng.randint(4, 50), rng.randint(1, 3)))
        designs = _shuffled(rng, designs)
        totals = [b + sum(counts[f] * (c if f in cov else scan) for f in range(4))
                  for cov, b, c in designs]
        if sorted(totals)[0] != sorted(totals)[1]:
            break
    best = min(range(5), key=lambda i: totals[i])

    wl = [Pred("lookups", Ident(fields[f]), Num(counts[f])) for f in range(4)]
    dfacts = [Pred("design", Ident(ids[i]), Num(designs[i][1]), Num(designs[i][2])) for i in range(5)]
    dfacts += [Pred("indexes", Ident(ids[i]), Ident(fields[f])) for i in range(5) for f in designs[i][0]]
    obs = Rec(store=Lst([Pred("scan_cost", Num(scan))]),
              workload=Lst(_shuffled(rng, wl)),
              designs=Lst(_shuffled(rng, dfacts)),
              rules=_rules("design_lists_build_cost_and_cost_per_indexed_lookup",
                           "a_lookup_on_an_unindexed_field_costs_scan_cost",
                           "total_cost_is_build_cost_plus_sum_over_fields_of_lookups_times_per_lookup_cost"),
              query=Ident("cheapest_memory_design"))
    return (obs, _shuffled(rng, ids), ids[best],
            {"totals": {ids[i]: totals[i] for i in range(5)}, "scan_cost": scan})


class ExternalMemoryDesign(Lesson):
    """Index a symbolic store for its retrieval workload."""

    id = "external_memory_design"
    number = 142
    level = 142
    section = "xiii"
    section_title = "self-modeling and architecture adaptation"
    teaches = "index a symbolic store for its retrieval workload"
    capabilities = ('architecture_adaptation', 'abstraction', 'metareasoning')
    axes = {'reasoning_depth': 4, 'world_complexity': 3, 'compositional_depth': 3}

    generate = staticmethod(gen_external_memory_design)
