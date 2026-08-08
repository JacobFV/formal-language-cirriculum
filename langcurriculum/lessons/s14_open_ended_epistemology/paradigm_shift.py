"""Lesson 149: ``paradigm_shift`` — the assumption a new regime falsifies.

Open-ended epistemology.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Num, Pred, Rec, Str
from ...lesson import Lesson
from ..._support.selfmodel import ASSUMPTIONS, _assumption_status, _rules, _shuffled


def gen_paradigm_shift(rng: random.Random):
    """A framework that held in the old regime; exactly one assumption dies in the new one.

    Every assumption is a testable predicate over the series and all four hold on
    the old data. The new data falsifies exactly one — verified by evaluating all
    four rather than by construction alone — so patching the other three is
    provably the wrong response.
    """
    bound = rng.choice([80, 100, 120])
    step = rng.choice([5, 6, 7])
    target = rng.choice(ASSUMPTIONS)
    for _ in range(200):
        start = rng.randint(2, 10)
        old = [start]
        for _ in range(5):
            old.append(old[-1] + rng.randint(1, step))
        if not all(_assumption_status(old, bound, step).values()):
            continue
        if target == "positivity":
            s = rng.randint(-6, -1)
            new = [s]
            for _ in range(5):
                new.append(new[-1] + rng.randint(1, step))
        elif target == "monotonicity":
            new = [rng.randint(3, 12)]
            for _ in range(5):
                new.append(new[-1] + rng.randint(1, step))
            i = rng.randrange(len(new) - 1)
            new[i], new[i + 1] = new[i + 1], new[i]
        elif target == "boundedness":
            new = [bound - rng.randint(1, 4)]
            for _ in range(5):
                new.append(new[-1] + rng.randint(1, step))
        else:
            new = [rng.randint(2, 8)]
            jump = rng.randrange(5)
            for k in range(5):
                new.append(new[-1] + (rng.randint(step + 2, step + 9) if k == jump
                                      else rng.randint(1, step)))
        st = _assumption_status(new, bound, step)
        broken = [a for a in ASSUMPTIONS if not st[a]]
        if broken == [target]:
            break

    obs = Rec(framework=Lst([Pred("assumes", Ident("positivity"), Str("every value is positive")),
                             Pred("assumes", Ident("monotonicity"), Str("every value exceeds the previous one")),
                             Pred("assumes", Ident("boundedness"), Str("every value is below the bound")),
                             Pred("assumes", Ident("small_steps"), Str("consecutive values differ by at most the step"))]),
              constants=Lst([Pred("bound", Num(bound)), Pred("step", Num(step))]),
              old_regime=Lst([Pred("reading", Num(i), Num(v)) for i, v in enumerate(old)]),
              new_regime=Lst([Pred("reading", Num(i), Num(v)) for i, v in enumerate(new)]),
              rules=_rules("the_framework_holds_in_a_regime_iff_all_four_assumptions_hold_of_its_readings",
                           "name_the_assumption_the_new_regime_falsifies"),
              query=Ident("falsified_assumption"))
    return (obs, _shuffled(rng, list(ASSUMPTIONS)), target,
            {"old": old, "new": new, "bound": bound, "step": step})


class ParadigmShift(Lesson):
    """The assumption a new regime falsifies."""

    id = "paradigm_shift"
    number = 149
    level = 149
    section = "xiv"
    section_title = "open-ended epistemology"
    teaches = "the assumption a new regime falsifies"
    capabilities = ('scientific_induction', 'open_ended_discovery', 'abstraction')
    axes = {'reasoning_depth': 4, 'world_complexity': 3, 'ambiguity': 2}
    answers = ['positivity', 'monotonicity', 'boundedness', 'small_steps']

    generate = staticmethod(gen_paradigm_shift)
