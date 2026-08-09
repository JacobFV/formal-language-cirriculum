"""Spanish: gender and number concord, post-nominal adjectives, ¿inverted?

Ported from the template pack it replaces, with every behaviour that pack's
tests asserted kept intact — including the two that are easy to lose.

**Concord is now unification, not a special case.** The template pack agreed
adjectives by calling ``Adjective.agree(gender, plural)`` at each of a hundred
call sites. Here the noun's gender is an inherent feature, the linearizer's
:class:`~langcurriculum.grammar.linearize.Concord` declares that adjectives and
determiners share it, and agreement happens once in the walk. The same
declaration, over an inventory nine times larger, is what makes Swahili work.

**el agua.** A feminine noun beginning with a stressed /a/ takes the *masculine*
article while its adjectives still agree as feminine: *el agua fría*, *las aguas
frías*. It is the one place in Spanish where the article and the adjective
disagree about gender, and a concord system that propagates one feature to both
gets it wrong by construction. The determiner therefore reads the noun's
phonology, not just its class.

**ser and estar.** Identity takes *ser*, location takes *estar*. The engine asks
:meth:`~langcurriculum.grammar.linearize.Grammar.copula` which kind of predication
it is building, so this is three lines rather than a parallel template table.

Not attempted
-------------

Subjunctive, clitic pronouns, agreement across a relative clause. Nothing in the
curriculum's structures needs them and guessing produces exactly the
confident-sounding errors this grammar exists to avoid.
"""

from __future__ import annotations

import re
from typing import Any

from ..category import A, CLS, N, NUM, PL
from ..features import EMPTY, FS
from ..linearize import (
    NO_CASE, Alignment, Concord, Typography, WordOrder,
)
from ..morphology import Morphology
from ..syntax import Node
from .vocab import VocabularyGrammar

__all__ = ["Spanish", "EL_AGUA"]

#: Feminine nouns beginning with a stressed /a/. They take *el* in the singular
#: and *las* in the plural, and their adjectives are feminine throughout.
EL_AGUA = frozenset({
    "agua", "área", "arma", "aula", "alma", "hambre", "águila", "ala",
    "acta", "hacha", "ancla", "aria", "asa", "hada", "ave", "haba", "alba",
})

_I_INITIAL = re.compile(r"^[iíhH]?[ií]", re.IGNORECASE)
_O_INITIAL = re.compile(r"^(h?o)", re.IGNORECASE)

_ARTICLES = {
    ("def", "m", False): "el", ("def", "f", False): "la",
    ("def", "m", True): "los", ("def", "f", True): "las",
    ("indef", "m", False): "un", ("indef", "f", False): "una",
    ("indef", "m", True): "unos", ("indef", "f", True): "unas",
}

_CLOSED = {
    "and": "y", "or": "o", "not": "no", "of": "de", "if": "si",
    "then": "entonces", "to": "a", "at": "en", "empty": "nada",
    "what": "qué", "which": "cuál", "who": "quién", "where": "dónde",
    "when": "cuándo", "why": "por qué", "how": "cómo",
    "how_many": "cuántos",
    "all": "todos", "some": "algunos", "none": "ninguno",
    "most": "la mayoría", "few": "pocos", "exactly_two": "exactamente dos",
    "gt": "es mayor que", "lt": "es menor que",
    "ge": "es al menos", "le": "es como máximo",
    "eq": "es igual a", "neq": "no es igual a",
    "step": "paso", "round": "ronda", "trial": "ensayo", "turn": "turno",
    "case": "caso", "block": "bloque", "stage": "etapa",
    "is": "es", "are": "son",
}

_RELATIONS = {
    "imp": "implica", "implies": "implica", "iff": "si y sólo si",
    "entails": "implica", "supports": "apoya a", "attacks": "ataca a",
    "contradicts": "contradice a", "isa": "es un", "is_a": "es un",
    "requires": "requiere", "provides": "proporciona", "feeds": "alimenta a",
    "causes": "causa", "precedes": "precede a", "after": "después de",
    "means": "significa", "says": "dice", "claims": "afirma que",
    "has": "tiene", "holds": "se cumple para",
    "add": "más", "sub": "menos", "mul": "por", "div": "dividido por",
    "mod": "módulo", "pow": "elevado a",
    "left_of": "a la izquierda de", "right_of": "a la derecha de",
    "above": "encima de", "below": "debajo de", "near": "cerca de",
    "inside": "dentro de", "front_of": "delante de", "behind": "detrás de",
    "on": "sobre",
}


def _pluralize(word: str) -> str:
    """Regular Spanish plural, for a word the vocabulary does not carry."""
    if not word:
        return word
    if word[-1] in "aeiouáéíóú":
        return word + "s"
    if word.endswith("z"):
        return word[:-1] + "ces"
    return word + "es"


class SpanishNoun(Morphology):
    """Plural from the vocabulary, with the regular rule as the fallback."""

    def __init__(self, vocabulary):
        self.by_lemma = {n.lemma: n for n in vocabulary.nouns.values()}

    def inflect(self, lemma: str, feats: FS = EMPTY) -> str:
        if feats.get_atom(NUM) != PL:
            return lemma
        noun = self.by_lemma.get(lemma)
        if noun is not None and noun.plural:
            return noun.plural
        return _pluralize(lemma)

    def forms(self, lemma: str) -> set[str]:
        return {lemma, self.inflect(lemma, FS({NUM: PL}))}


class SpanishAdjective(Morphology):
    """Four agreement forms, selected by the class and number that reach it."""

    def __init__(self, vocabulary):
        self.by_base = {}
        for a in vocabulary.adjectives.values():
            for form in (a.base, a.ms, a.fs, a.mp, a.fp):
                if form:
                    self.by_base.setdefault(form, a)

    def inflect(self, lemma: str, feats: FS = EMPTY) -> str:
        adjective = self.by_base.get(lemma)
        if adjective is None:
            return lemma
        return adjective.agree(feats.get_atom(CLS, "m") or "m",
                               plural=feats.get_atom(NUM) == PL)

    def forms(self, lemma: str) -> set[str]:
        a = self.by_base.get(lemma)
        return {lemma} if a is None else {f for f in (a.base, a.ms, a.fs, a.mp, a.fp) if f}


class Spanish(VocabularyGrammar):
    """Spanish prose, on the grammar engine."""

    code = "spanish"
    name = "Spanish"
    pack = "spanish"
    iso = "spa"

    order = WordOrder(
        clause="SVO", adj="NA", det="DN", numeral="NumN",
        adposition="pre", possessive="NG", label="LV", conditional="CA",
        wh_fronting=True, copula_overt=True, numeral_forces_plural=True,
        negation="pre",
    )
    typography = Typography(question_open="¿", question_mark="?",
                            label_separator=":")
    alignment = Alignment(case_of=NO_CASE)
    #: the declaration that replaces a hundred calls to ``agree()``
    concord = Concord(adjective=(CLS, NUM), determiner=(CLS, NUM),
                      predicative=(CLS, NUM))

    notes = (
        "gender and number concord on articles and adjectives",
        "adjectives follow the noun",
        "ser for identity, estar for location",
        "the el agua exception: masculine article, feminine adjective",
        "inverted opening question mark",
        "y/e before i-/hi- and o/u before o-/ho-",
        "plural from the vocabulary, regular -s/-es/-ces otherwise",
        "NOT attempted: subjunctive, clitic pronouns, agreement across a "
        "relative clause",
    )

    def __init__(self) -> None:
        super().__init__()
        self.closed = {**_CLOSED, **self.closed}
        self.predicate_words = {**_RELATIONS, **self.predicate_words}
        self.paradigms = {
            "pronouns": {"f": "ella", "m": "él"},
            "name_gender": {"alice": "f", "bob": "m", "carol": "f",
                            "dave": "m", "erin": "f", "frank": "m"},
        }
        self.morphology[N.name] = SpanishNoun(self.vocabulary)
        self.morphology[A.name] = SpanishAdjective(self.vocabulary)

    # ---- the article, including the one exception -------------------------
    def determiner(self, kind: str, head: Node | None, feats: FS) -> str:
        """``el``/``la``/``los``/``las`` and ``un``/``una``, agreeing with the noun.

        The *el agua* rule lives here rather than in the concord declaration
        because it is a fact about the article alone: the adjective in the same
        phrase stays feminine. Propagating a single gender feature to both, as
        concord does everywhere else, would produce *el agua frío*.
        """
        if kind not in ("def", "indef"):
            return ""
        gender = feats.get_atom(CLS, "m") or "m"
        plural = feats.get_atom(NUM) == PL
        if gender == "f" and not plural and head is not None:
            surface = self.word(head.lemma, pos="N")
            if surface.lower() in EL_AGUA:
                gender = "m"
        return _ARTICLES.get((kind, gender, plural), "")

    # ---- coordination -----------------------------------------------------
    def join_list(self, items):
        """``a, b y c`` — with ``y`` becoming ``e`` before *i-* or *hi-*."""
        items = [i for i in items if i]
        if len(items) <= 1:
            return items[0] if items else ""
        conj = "e" if _I_INITIAL.match(items[-1]) else "y"
        return f"{self.typography.list_separator.join(items[:-1])} {conj} {items[-1]}"

    def disjoin(self, items):
        """``siete u ocho`` — ``o`` becomes ``u`` before *o-* or *ho-*."""
        items = [i for i in items if i]
        if len(items) <= 1:
            return items[0] if items else ""
        conj = "u" if _O_INITIAL.match(items[-1]) else "o"
        return f"{self.typography.list_separator.join(items[:-1])} {conj} {items[-1]}"

    # ---- ser and estar ----------------------------------------------------
    def copula(self, kind: str, feats: FS) -> str:
        """*ser* for what a thing is, *estar* for where it is."""
        plural = feats.get_atom(NUM) == PL
        if kind == "loc":
            return "están" if plural else "está"
        return "son" if plural else "es"

    # ---- labels -----------------------------------------------------------
    _TRAILING = (" de", " a", " para", " en", " con", " que")

    def clean_label(self, label: str) -> str:
        """Drop a trailing preposition: it needs a complement that is not there."""
        for tail in self._TRAILING:
            if label.endswith(tail):
                return label[: -len(tail)]
        return label

    def lin_Labelled(self, node: Node, ctx: FS) -> str:
        label, value = node.arg("label"), node.arg("value")
        assert label is not None and value is not None
        return (f"{self.clean_label(self.lin(label, ctx))}"
                f"{self.typography.colon} {self.lin(value, ctx)}")
