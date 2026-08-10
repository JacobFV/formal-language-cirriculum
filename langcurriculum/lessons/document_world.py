"""``document_world`` — multi-passage entity and event reconciliation.

Analogy, causality, planning, and programs.
"""

from __future__ import annotations

import random

from .._structure import Ident, Lst, Num, Pred, Rec
from ..lesson import Lesson
from ..generators.base import NAMES
from ..generators.social import CITIES, COMPANIES, _shuffled


def gen_document_world(rng: random.Random):
    """Employment history in one passage, geography in another, a lure in a third.

    No passage contains the answer. The employment passage names no city, the
    geography passage names no person, and a travel passage attaches the person to
    a city that is *not* the answer — so a reader that grabs the nearest
    person-city co-occurrence is wrong on purpose. The employment passage also has
    to be reconciled over time: the person joined one employer, left it, and
    joined another.
    """
    people = rng.sample(NAMES, 3)
    firms = rng.sample(COMPANIES, 3)
    cities = rng.sample(CITIES, 4)
    answer_city = cities[0]
    subject = people[0]
    old_firm, new_firm = firms[0], firms[1]
    hq = {new_firm: answer_city, old_firm: cities[1], firms[2]: cities[2]}
    lure_city = cities[3]

    y0 = rng.randint(2001, 2008)
    employment = [Pred("joined", Ident(subject), Ident(old_firm), Num(y0)),
                  Pred("left", Ident(subject), Ident(old_firm), Num(y0 + rng.randint(2, 5)))]
    joined_year = y0 + rng.randint(6, 9)
    employment.append(Pred("joined", Ident(subject), Ident(new_firm), Num(joined_year)))
    for other, firm in zip(people[1:], firms[1:]):                    # distractor employees
        employment.append(Pred("joined", Ident(other), Ident(firm), Num(rng.randint(2001, 2015))))

    geography = [Pred("headquarters", Ident(f), Ident(c)) for f, c in hq.items()]
    travel = [Pred("visited", Ident(subject), Ident(lure_city), Num(joined_year + 1)),
              Pred("visited", Ident(people[1]), Ident(hq[firms[2]]), Num(joined_year + 2))]

    passages = [Pred("passage", Pred("p_employment"), Lst(_shuffled(rng, employment))),
                Pred("passage", Pred("p_geography"), Lst(_shuffled(rng, geography))),
                Pred("passage", Pred("p_travel"), Lst(_shuffled(rng, travel)))]
    obs = Rec(document=Lst(_shuffled(rng, passages)),
              query=Pred("works_in_city", Ident(subject)))
    vocab = _shuffled(rng, sorted(set(list(hq.values()) + [lure_city])))
    return (obs, vocab, answer_city,
            {"subject": subject, "current_employer": new_firm, "former_employer": old_firm,
             "headquarters": dict(hq), "lure_city": lure_city})


class DocumentWorld(Lesson):
    """Multi-passage entity and event reconciliation."""

    id = "document_world"
    level = 52
    tags = ("analogy", "causality", "planning", "programs")
    teaches = "multi-passage entity and event reconciliation"
    capabilities = ('abstraction', 'temporal_reasoning')
    axes = {'discourse_horizon': 4, 'world_complexity': 4, 'reasoning_depth': 3}

    generate = staticmethod(gen_document_world)
