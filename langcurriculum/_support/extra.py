"""Support for the supplementary syntax and semantics lessons.

Private. Ported alongside the lessons that use it; every function here is
called by at least one generator in :mod:`langcurriculum.lessons`.
"""

from __future__ import annotations

import random
from typing import Any, Mapping, Sequence

from .._structure import Ident, Lst, Num, Pred, Term
from ..languages import DEFAULT_LANGUAGE, get_language
from .base import COLORS, SHAPES


def _active_lexicon():
    """The lexicon the morphology lessons draw their inflected material from."""
    return get_language(DEFAULT_LANGUAGE).lexicon

# The syntax lessons in this section are *about* morphology — agreement across a
# long dependency, pronoun resolution, center embedding — so they need real
# inflected material rather than nonce words. It comes from the active language
# pack, which is what makes those lessons portable: a pack for another language
# supplies its own verbs, noun forms and pronouns and the lessons keep working.
_LEXICON = _active_lexicon()

VERBS = list(_LEXICON.verbs)


INTRANSITIVE = list(_LEXICON.intransitive_verbs)


ADVERBS = list(_LEXICON.adverbs)


PREPOSITIONS = list(_LEXICON.preposition_words)


NOUN_FORMS = [tuple(x) for x in _LEXICON.noun_forms]


AGREE_FORMS = [tuple(x) for x in _LEXICON.agreement_forms]


GENDER = dict(_LEXICON.name_gender)


PRONOUN = dict(_LEXICON.pronouns)


SIZES = ["small", "big"]


NONCE_LETTERS = "kmtszlpvr"


def _shuffled(rng: random.Random, xs: Sequence[Any]) -> list[Any]:
    """A shuffled copy. Every answer vocabulary in this module goes through it."""
    ys = list(xs)
    rng.shuffle(ys)
    return ys


def _nonce(rng: random.Random, n: int = 3) -> str:
    return "".join(rng.choice(NONCE_LETTERS) for _ in range(n))


def _objects(rng: random.Random, n: int, *, distinct_colors: bool = False,
             distinct_shapes: bool = False) -> list[dict[str, Any]]:
    """``n`` objects with *shuffled* id labels, so an id never predicts a role."""
    ids = _shuffled(rng, [f"o{i}" for i in range(n)])
    colors = rng.sample(COLORS, n) if distinct_colors else [rng.choice(COLORS) for _ in range(n)]
    shapes = rng.sample(SHAPES, n) if distinct_shapes else [rng.choice(SHAPES) for _ in range(n)]
    return [{"id": ids[i], "color": colors[i], "shape": shapes[i]} for i in range(n)]


def _obj_list(objs: Sequence[Mapping[str, Any]]) -> Term:
    return Lst([Pred("obj", Ident(o["id"]), Ident(o["color"]), Ident(o["shape"])) for o in objs])


def _yesno(rng: random.Random, truth: bool) -> tuple[list[str], str]:
    return _shuffled(rng, ["yes", "no"]), ("yes" if truth else "no")


def _nest(rng: random.Random, depth: int) -> str:
    """A bracket string whose maximum nesting depth is exactly ``depth``."""
    if depth <= 0:
        return ""
    s = "(" + _nest(rng, depth - 1) + ")"
    if rng.random() < 0.4:
        s = s + "()" if rng.random() < 0.5 else "()" + s
    return s


def _max_depth(s: str) -> int:
    d = best = 0
    for c in s:
        d += 1 if c == "(" else -1
        best = max(best, d)
    return best


_OPS = ("+", "-", "*")


def _expr(rng: random.Random, depth: int) -> tuple[Term, int]:
    if depth <= 0 or rng.random() < 0.25:
        v = rng.randint(1, 5)
        return Num(v), v
    op = rng.choice(_OPS)
    left, lv = _expr(rng, depth - 1)
    right, rv = _expr(rng, depth - 1)
    val = {"+": lv + rv, "-": lv - rv, "*": lv * rv}[op]
    return Pred(op, left, right), val


def _items(objs: Sequence[Mapping[str, Any]]) -> Term:
    return Lst([Pred("item", Ident(o["id"]), Ident(o["color"]), Ident(o["shape"]),
                     Num(o["size"]), Num(o["x"])) for o in objs])


def _formula(rng: random.Random, objs: Sequence[Mapping[str, Any]]) -> tuple[Term, list[str], str]:
    """A random boolean formula over colour/shape, plus the ids it denotes."""
    def prop() -> tuple[Term, Any]:
        if rng.random() < 0.5:
            c = rng.choice(COLORS)
            return Pred("color", Ident(c)), lambda o: o["color"] == c
        s = rng.choice(SHAPES)
        return Pred("shape", Ident(s)), lambda o: o["shape"] == s

    form = rng.choice(["and", "or", "and_not", "not_and", "not"])
    p, fp = prop()
    q, fq = prop()
    if form == "and":
        sym, test = Pred("and", p, q), lambda o: fp(o) and fq(o)
    elif form == "or":
        sym, test = Pred("or", p, q), lambda o: fp(o) or fq(o)
    elif form == "and_not":
        sym, test = Pred("and", p, Pred("not", q)), lambda o: fp(o) and not fq(o)
    elif form == "not_and":
        sym, test = Pred("and", Pred("not", p), q), lambda o: (not fp(o)) and fq(o)
    else:
        sym, test = Pred("not", p), lambda o: not fp(o)
    return sym, [o["id"] for o in objs if test(o)], form
