"""``multi_objective_reasoning`` — which option the Pareto front excludes.

Values and goal cognition.
"""

from __future__ import annotations

import random

from .._structure import Ident, Lst, Num, Pred, Rec
from ..lesson import Lesson
from ..generators.selfmodel import _labels, _rules, _shuffled


def gen_multi_objective_reasoning(rng: random.Random):
    """Which option is dominated — worse on nothing, better on nothing.

    Three objectives, all "higher is better", and exactly one option that some
    other option beats or matches on every axis. Scalarizing would answer a
    different question; the answer here is a fact about the Pareto front.
    """
    objectives = rng.sample(["throughput", "accuracy", "coverage", "robustness"], 3)
    for _ in range(200):
        vals = [[rng.randint(1, 9) for _ in range(3)] for _ in range(4)]

        def dominated(i: int) -> bool:
            return any(j != i and all(vals[j][k] >= vals[i][k] for k in range(3))
                       and any(vals[j][k] > vals[i][k] for k in range(3)) for j in range(4))

        bad = [i for i in range(4) if dominated(i)]
        if len(bad) == 1:
            break
    ids = _labels(rng, "option", 4)
    facts = [Pred("scores", Ident(ids[i]), Ident(objectives[k]), Num(vals[i][k]))
             for i in range(4) for k in range(3)]
    obs = Rec(objectives=Lst([Pred("maximize", Ident(o)) for o in _shuffled(rng, objectives)]),
              options=Lst(_shuffled(rng, facts)),
              rules=_rules("option_a_dominates_option_b_iff_a_is_at_least_as_good_on_every_objective_and_better_on_one",
                           "exactly_one_option_is_dominated"),
              query=Ident("dominated_option"))
    return (obs, _shuffled(rng, ids), ids[bad[0]],
            {"values": {ids[i]: vals[i] for i in range(4)}, "objectives": objectives})


class MultiObjectiveReasoning(Lesson):
    """Which option the Pareto front excludes."""

    id = "multi_objective_reasoning"
    level = 158
    tags = ("values", "goals")
    teaches = "which option the Pareto front excludes"
    capabilities = ('value_learning', 'planning')
    axes = {'reasoning_depth': 4, 'world_complexity': 3, 'compositional_depth': 3}

    generate = staticmethod(gen_multi_objective_reasoning)
