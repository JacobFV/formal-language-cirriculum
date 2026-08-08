"""Lesson 106: ``hierarchical_planning`` — abstract methods expanded to executable primitives.

Problem formulation and hierarchical agency.
"""

from __future__ import annotations

import random

from ..._structure import Ident, Lst, Pred, Rec
from ...lesson import Lesson
from ..._support.epistemics import _labelled, _nonces, _run_method, _shuffled


def gen_hierarchical_planning(rng: random.Random):
    """Abstract actions expand into primitives; only one expansion executes.

    Each candidate method is a sequence of abstract subtasks, each of which
    expands into primitive operators with preconditions and effects. Executing
    the full expansion from the initial state decides the question: exactly one
    method both never violates a precondition and reaches the goal, and the
    other three are re-simulated to confirm they fail.
    """
    for _ in range(400):
        atoms = _nonces(rng, 6, 4)
        prim_names = _nonces(rng, 6, 4, avoid=atoms)
        task_names = _nonces(rng, 4, 4, avoid=atoms + prim_names)
        state0 = sorted(rng.sample(atoms, 2))
        a1, a2, goal = [a for a in atoms if a not in state0][:3]
        prims = {
            prim_names[0]: (list(state0[:1]), [a1]),
            prim_names[1]: ([a1], [a2]),
            prim_names[2]: ([a2], [goal]),
            prim_names[3]: ([goal], [atoms[-1]]),          # useless unless goal already holds
            prim_names[4]: ([a2, atoms[-1]], [a1]),        # unsatisfiable early
            prim_names[5]: (list(state0[1:2]), [atoms[-1]]),
        }
        expansions = {
            task_names[0]: [prim_names[0], prim_names[1]],
            task_names[1]: [prim_names[2]],
            task_names[2]: [prim_names[4], prim_names[3]],
            task_names[3]: [prim_names[5]],
        }
        methods = [
            [task_names[0], task_names[1]],
            [task_names[1], task_names[0]],
            [task_names[3], task_names[0]],
            [task_names[2], task_names[1]],
        ]
        oks = [_run_method(m, expansions, prims, state0, goal) for m in methods]
        if oks == [True, False, False, False]:
            break
    else:                                     # pragma: no cover - construction
        pass

    labs, answer = _labelled(rng, methods, 0)
    entries = [Pred("method", Ident(lab), Lst([Ident(t) for t in m]))
               for lab, m in zip(labs, methods)]
    obs = Rec(state=Lst([Ident(a) for a in state0]),
              operators=Lst(_shuffled(rng, [
                  Pred("primitive", Ident(p), Lst([Ident(x) for x in pre]),
                       Lst([Ident(x) for x in add])) for p, (pre, add) in prims.items()])),
              task_methods=Lst(_shuffled(rng, [
                  Pred("expands_to", Ident(t), Lst([Ident(p) for p in ps]))
                  for t, ps in expansions.items()])),
              candidates=Lst(_shuffled(rng, entries)),
              query=Pred("method_achieving", Ident(goal)))
    return (obs, _shuffled(rng, labs), answer,
            {"goal": goal, "answer": answer, "initial_state": state0})


class HierarchicalPlanning(Lesson):
    """Abstract methods expanded to executable primitives."""

    id = "hierarchical_planning"
    number = 106
    level = 106
    section = "ix"
    section_title = "problem formulation and hierarchical agency"
    teaches = "abstract methods expanded to executable primitives"
    capabilities = ('hierarchical_planning', 'planning', 'simulation')
    axes = {'reasoning_depth': 4, 'planning_horizon': 4, 'recursion_depth': 2}

    generate = staticmethod(gen_hierarchical_planning)
