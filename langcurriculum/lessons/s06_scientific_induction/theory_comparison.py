"""Lesson 71: ``theory_comparison`` — rival theories, identical fit, one held-out datum.

Scientific induction and model discovery.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Num, Pred, Rec, Term
from ...lesson import Lesson
from ..._support.science import _add, _labels, _mul, _shuffled, _sub


def gen_theory_comparison(rng: random.Random):
    """Four theories fit the observations *exactly*; a new datum kills three.

    The rivals are built as ``p·x + q + k·(x-s)(x-t)(x-u)`` over the three
    training points, so they are indistinguishable on the training set by
    construction — no amount of re-fitting separates them — and the held-out
    observation is the only evidence that does. Simplicity is a real but
    insufficient cue: the ``k = 0`` theory is the simplest one and is right a
    quarter of the time.
    """
    for _ in range(300):
        s, t, u = rng.sample(range(-5, 6), 3)
        p = rng.choice([-3, -2, -1, 1, 2, 3])
        q = rng.randint(-6, 6)
        ks = [0] + rng.sample([-2, -1, 1, 2], 3)
        pool = [v for v in range(-7, 8) if v not in (s, t, u)]
        xh = rng.choice(pool)
        dh = (xh - s) * (xh - t) * (xh - u)
        if dh == 0:
            continue
        vals = [p * xh + q + k * dh for k in ks]
        if len(set(vals)) != 4:
            continue
        true_i = rng.randrange(4)
        order = _shuffled(rng, range(4))
        labels = _labels("t", 4)
        answer = labels[order.index(true_i)]

        def theory(k: int) -> Term:
            base = _add(_mul(Num(p), Ident("x")), Num(q))
            if k == 0:
                return base
            cubic = _mul(_sub(Ident("x"), Num(s)), _mul(_sub(Ident("x"), Num(t)),
                                                        _sub(Ident("x"), Num(u))))
            return _add(base, _mul(Num(k), cubic))

        obs = Rec(data=Lst([Pred("observed", Num(x), Num(p * x + q)) for x in (s, t, u)]),
                  theories=Lst([Pred("theory", Ident(labels[j]),
                                     Pred("eq", Ident("y"), theory(ks[i])))
                                for j, i in enumerate(order)]),
                  new_observation=Pred("observed", Num(xh), Num(vals[true_i])),
                  query=Ident("surviving_theory"))
        hidden = {"k_true": ks[true_i], "coefficients": [p, q], "roots": [s, t, u],
                  "x_new": xh, "answer": answer}
        return obs, _shuffled(rng, labels), answer, hidden
    raise RuntimeError("theory_comparison: no admissible episode")


class TheoryComparison(Lesson):
    """Rival theories, identical fit, one held-out datum."""

    id = "theory_comparison"
    number = 71
    level = 71
    section = "vi"
    section_title = "scientific induction and model discovery"
    teaches = "rival theories, identical fit, one held-out datum"
    capabilities = ('scientific_induction', 'abstraction')
    axes = {'reasoning_depth': 4, 'compositional_depth': 4, 'ambiguity': 2}

    generate = staticmethod(gen_theory_comparison)
