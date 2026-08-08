"""Lesson 159: ``goal_inference`` — the goal that explains all of the behaviour.

Values and goal cognition.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Pred, Rec
from ...lesson import Lesson
from ..._support.base import COLORS, SHAPES
from ..._support.selfmodel import SIZES, _labels, _rules, _shuffled


def gen_goal_inference(rng: random.Random):
    """Which goal explains everything the observed agent took, and nothing it left.

    The agent's picks are exactly the extension of one candidate goal; the other
    candidates each over- or under-cover, so a goal that merely explains most of
    the behaviour is not good enough.
    """
    for _ in range(200):
        items = [{"id": f"i{i}", "color": rng.choice(COLORS[:3]), "shape": rng.choice(SHAPES[:3]),
                  "size": rng.choice(SIZES)} for i in range(6)]
        opts = [(a, v) for a in ("color", "shape", "size")
                for v in {"color": COLORS[:3], "shape": SHAPES[:3], "size": SIZES}[a]]
        true = rng.choice(opts)
        picked = {it["id"] for it in items if it[true[0]] == true[1]}
        if not (1 <= len(picked) <= 4):
            continue
        others = [o for o in opts if o != true
                  and {it["id"] for it in items if it[o[0]] == o[1]} != picked]
        if len(others) >= 3:
            break
    cands = [true] + rng.sample(others, 3)
    ids = _labels(rng, "goal", 4)
    facts = [Pred("item", Ident(it["id"]), Ident(it["color"]), Ident(it["shape"]), Ident(it["size"]))
             for it in items]
    facts += [Pred("collected", Ident(i)) for i in sorted(picked)]
    gfacts = [Pred("goal", Ident(ids[i]), Ident(cands[i][0]), Ident(cands[i][1])) for i in range(4)]
    obs = Rec(episode=Lst(_shuffled(rng, facts)),
              goals=Lst(_shuffled(rng, gfacts)),
              rules=_rules("an_agent_pursuing_a_goal_collects_exactly_the_items_matching_that_goals_attribute_and_value",
                           "exactly_one_candidate_goal_explains_the_observed_behaviour"),
              query=Ident("which_goal"))
    return (obs, _shuffled(rng, ids), ids[0],
            {"goal": list(true), "collected": sorted(picked)})


class GoalInference(Lesson):
    """The goal that explains all of the behaviour."""

    id = "goal_inference"
    number = 159
    level = 159
    section = "xv"
    section_title = "values and goal cognition"
    teaches = "the goal that explains all of the behaviour"
    capabilities = ('belief_modeling', 'value_learning')
    axes = {'reasoning_depth': 4, 'world_complexity': 3, 'ambiguity': 2}

    generate = staticmethod(gen_goal_inference)
