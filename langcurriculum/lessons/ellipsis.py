"""``ellipsis`` — recovering elided structure.

Language as action.
"""

from __future__ import annotations

import random

from .._structure import Ident, Lst, Num, Pred, Rec
from ..lesson import Lesson
from ..generators.base import NAMES
from ..generators.semantics import OBJECTS, TRANS_VERBS, _shuffled


def gen_ellipsis(rng: random.Random):
    """Recover elided structure: gapping and VP-ellipsis.

    ``alice likes tea and bob coffee`` (the verb is gapped: what does bob do?)
    and ``alice likes tea and bob does too`` (the VP is elided: what does bob
    like?). Distractor clauses precede the antecedent so the answer is never the
    only verb or the only object in the discourse.
    """
    subs = rng.sample(NAMES, 4)
    verbs = rng.sample(TRANS_VERBS, 3)
    objs = rng.sample(OBJECTS, 4)
    mode = rng.choice(["gapping", "vp_ellipsis"])

    clauses = [(subs[2], verbs[1], objs[1]), (subs[3], verbs[2], objs[2])]
    rng.shuffle(clauses)
    antecedent = (subs[0], verbs[0], objs[0])
    clauses.append(antecedent)

    lines = [Pred("clause", Num(i), Ident(s), Ident(v), Ident(o))
             for i, (s, v, o) in enumerate(clauses)]
    i = len(clauses)
    if mode == "gapping":
        lines.append(Pred("gap", Num(i), Ident(subs[1]), Ident(objs[3])))
        query = Pred("verb_of", Ident(subs[1]))
        vocab, answer = _shuffled(rng, TRANS_VERBS), antecedent[1]
    else:
        lines.append(Pred("vp_gap", Num(i), Ident(subs[1])))
        query = Pred("object_of", Ident(subs[1]))
        vocab, answer = _shuffled(rng, OBJECTS), antecedent[2]

    obs = Rec(discourse=Lst(lines), query=query)
    return obs, vocab, answer, {"mode": mode, "antecedent": list(antecedent)}


class Ellipsis(Lesson):
    """Recovering elided structure."""

    id = "ellipsis"
    level = 24
    tags = ("pragmatics", "language-as-action")
    teaches = "recovering elided structure"
    capabilities = ('recursive_syntax', 'variable_binding')
    axes = {'grammar_complexity': 3, 'compositional_depth': 3, 'discourse_horizon': 2}

    generate = staticmethod(gen_ellipsis)
