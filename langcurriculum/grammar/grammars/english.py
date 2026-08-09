"""English, as a set of parameters rather than a set of format strings.

The interesting thing about this file is how little is in it. English is SVO,
adjectives precede nouns, determiners precede adjectives, it is prepositional,
it fronts wh-words, and it has essentially no case on nouns and no agreement
worth the name. All of that is nine lines of :class:`WordOrder` and an
:class:`Alignment` that marks nothing.

What is left over is genuinely English: the phonological ``a``/``an``
alternation, and the fact that English forms polar questions by moving an
auxiliary to the front, which is typologically unusual enough that the
linearizer's default — a clause-final particle — is wrong for it and has to be
overridden. Two overrides. That is the target every other grammar in this
package should be measured against.
"""

from __future__ import annotations

import re

from ..category import N, NUM, PL, SG
from ..features import EMPTY, FS
from ..linearize import (
    NO_CASE, Alignment, Concord, Grammar, Typography, WordOrder,
)
from ..morphology import StoredMorphology
from ..syntax import Node
from .vocab import VocabularyGrammar

__all__ = ["English"]

#: article selection is phonological, so it is fixed after the words are chosen
_A_BEFORE_VOWEL = re.compile(r"\ba (?=[aeiou])")

_CLOSED = {
    "the": "the", "a": "a", "is": "is", "are": "are", "not": "not",
    "and": "and", "or": "or", "of": "of", "if": "if", "then": "then",
    "to": "to", "at": "at", "empty": "nothing", "q_particle": "",
    "what": "what", "which": "which", "who": "who", "where": "where",
    "when": "when", "why": "why", "how": "how", "how_many": "how many",
    "all": "all", "some": "some", "none": "no", "most": "most", "few": "few",
    "exactly_two": "exactly two",
    "gt": "is greater than", "lt": "is less than",
    "ge": "is at least", "le": "is at most",
    "eq": "equals", "neq": "does not equal",
    "step": "step", "round": "round", "trial": "trial", "turn": "turn",
    "case": "case", "block": "block", "stage": "stage",
}

#: the relational lexicon: a predicate head and the words that realize it
#: between two arguments. Kept here rather than in the data file only because
#: that is where the English pack has always had it.
_RELATIONS = {
    "imp": "implies", "implies": "implies", "iff": "if and only if",
    "entails": "entails", "supports": "supports", "attacks": "attacks",
    "contradicts": "contradicts", "isa": "is a", "is_a": "is a",
    "requires": "requires", "provides": "provides", "feeds": "feeds",
    "causes": "causes", "precedes": "comes before", "after": "after",
    "means": "means", "says": "says", "claims": "claims that",
    "has": "has", "holds": "holds of", "observed": "was observed to be",
    "predicts": "predicts", "add": "plus", "sub": "minus", "mul": "times",
    "div": "divided by", "mod": "modulo", "pow": "to the power",
    "left_of": "to the left of", "right_of": "to the right of",
    "above": "above", "below": "below", "near": "next to", "inside": "inside",
    "front_of": "in front of", "behind": "behind", "on": "on",
}

#: The minimal pairs the morphology lessons build from. These are not part of
#: the curriculum's *content* vocabulary — they are the raw material a lesson on
#: subject-verb agreement or centre-embedding needs in order to construct a
#: contrast, and they have to come from the language being presented.
_PARADIGMS = {
    "verbs": ("chased", "praised", "watched", "avoided", "greeted", "followed"),
    "intransitive_verbs": ("left", "smiled", "waited", "returned", "slept",
                           "laughed"),
    "adverbs": ("yesterday", "quietly", "again", "twice"),
    "noun_forms": (("key", "keys"), ("dog", "dogs"), ("author", "authors"),
                   ("farmer", "farmers"), ("book", "books"), ("pilot", "pilots")),
    "agreement_forms": (("opens", "open"), ("arrives", "arrive"),
                        ("works", "work"), ("fails", "fail"),
                        ("moves", "move"), ("waits", "wait")),
    "pronouns": {"f": "she", "m": "he"},
    "name_gender": {"alice": "f", "bob": "m", "carol": "f",
                    "dave": "m", "erin": "f", "frank": "m"},
    "preposition_words": ("near", "beside", "under", "behind", "by"),
}

_IRREGULAR = {
    "child": "children", "person": "people", "mouse": "mice", "foot": "feet",
    "tooth": "teeth", "goose": "geese", "man": "men", "woman": "women",
    "die": "dice", "index": "indices", "matrix": "matrices",
    "analysis": "analyses", "hypothesis": "hypotheses", "datum": "data",
}


def _plural(lemma: str, feats: FS) -> str:
    """Regular English pluralization, applied only when the features ask for it."""
    if feats.get_atom(NUM) != PL:
        return lemma
    if lemma in _IRREGULAR:
        return _IRREGULAR[lemma]
    if re.search(r"(s|x|z|ch|sh)$", lemma):
        return lemma + "es"
    if re.search(r"[^aeiou]y$", lemma):
        return lemma[:-1] + "ies"
    if re.search(r"[^f]f$", lemma):
        return lemma[:-1] + "ves"
    return lemma + "s"


class English(VocabularyGrammar):
    """English prose. The reference grammar and the regression baseline."""

    code = "english"
    name = "English"
    pack = "english"
    overlay = "english"

    order = WordOrder(
        clause="SVO", adj="AN", det="DN", numeral="NumN",
        adposition="pre", possessive="NG", label="LV", conditional="CA",
        wh_fronting=True, copula_overt=True,
    )
    typography = Typography()
    #: English marks no case on full noun phrases at all
    alignment = Alignment(case_of=NO_CASE)
    #: and agrees nothing with anything, inside the noun phrase
    concord = Concord()

    notes = (
        "SVO, determiner then adjective then noun, prepositional",
        "no case on nouns, no adjective agreement",
        "polar questions by auxiliary fronting — the one typological oddity",
        "indefinite article by phonology (a/an)",
        "regular -s/-es/-ies plural with stored irregulars",
    )

    def __init__(self) -> None:
        super().__init__()
        self.closed = {**_CLOSED, **self.closed}
        # the relational lexicon lives in code for English and in JSON for the
        # other packs; the engine reads it the same way either way
        self.predicate_words = {**_RELATIONS, **self.predicate_words}
        # only nouns inflect; adjectives and verbs are handled by the vocabulary
        self.morphology[N.name] = StoredMorphology(rule=_plural)
        self.paradigms = dict(_PARADIGMS)

    # ---- the two genuinely English things -------------------------------
    def sentence(self, text: str, end: str | None = None) -> str:
        """Fix ``a`` before a vowel once, after the words have been chosen."""
        return _A_BEFORE_VOWEL.sub("an ", super().sentence(text, end))

    def lin_Neg(self, node: Node, ctx: FS) -> str:
        """English negation attaches to a finite auxiliary, not to the clause.

        Neither ``pre`` nor ``post`` describes *the cube is not red*: the negator
        goes inside the predicate, after the copula. Languages that put it at one
        edge or the other are the common case and the parameter covers them;
        English is the outlier and pays for it with this override.
        """
        inner = node.arg("inner")
        assert inner is not None
        text = self.lin(inner, ctx)
        for aux in (" is ", " are ", " was ", " were ", " has ", " have "):
            if aux in text:
                head, _, rest = text.partition(aux)
                return f"{head}{aux.rstrip()} not {rest}"
        return self.join(["does not", text])

    def lin_WhQ(self, node: Node, ctx: FS) -> str:
        """``what is the X of Y?`` — English asks for a value with a copula.

        Fronting the wh-word is only half of it: English also needs a copula and
        a determiner that the abstract tree does not supply, because most
        languages do not need them. A head that already reads as a clause keeps
        its own shape.
        """
        body = node.arg("body")
        assert body is not None
        key = node.feats.get_atom("wh", "what")
        if key in self.WH_DETERMINERS and body.fn in ("NP", "CN"):
            return super().lin_WhQ(node, ctx)      # "which object is the …"
        wh = self.cw(key, "what")
        inner = self.lin(body, ctx)
        if body.fn in ("PredAttr", "PredIdent", "PredRel", "PredLoc"):
            return self.join([wh, inner])
        return self.join([wh, "is the", inner])

    def lin_YNQ(self, node: Node, ctx: FS) -> str:
        """English fronts an auxiliary rather than appending a particle.

        Typologically this is the marked strategy — most languages use a particle
        or intonation — so the linearizer's default is the particle and English
        is the one that overrides. Getting that polarity right is the difference
        between a grammar engine and an English engine with translations bolted
        on.
        """
        body = node.arg("body")
        assert body is not None
        inner = self.lin(body, ctx)
        # "the string is balanced" -> "is the string balanced"
        for aux in (" is ", " are ", " was ", " were ", " has ", " have "):
            if aux in inner:
                subject, _, rest = inner.partition(aux)
                return self.join([aux.strip(), subject, rest])
        return self.join(["does", inner])


class EnglishSynonym(English):
    """English whose *question* uses near-synonyms held out of training.

    The asymmetry is the whole test. The body of the episode keeps the words a
    model was trained on and only the question switches — ``red`` becomes
    ``crimson``, ``cube`` becomes ``block`` — so a learner has to connect a word
    it has never read to one it has. Substituting in both places would make the
    episode *easier* than the default rather than harder, which is why the scope
    is the question and nothing else.
    """

    code = "english_synonym"
    name = "English (held-out synonyms)"
    pack = "english"
    overlay = "english"

    notes = English.notes + (
        "the question's content words are near-synonyms held out of the body",
    )

    def __init__(self) -> None:
        super().__init__()
        self.synonyms = dict(self.raw.get("synonyms") or {})
        self._in_query = False

    def word(self, lemma: str, pos: str = "") -> str:
        surface = super().word(lemma, pos)
        return self.synonyms.get(surface, surface) if self._in_query else surface

    def question(self, node, ctx=None):
        """Substitute only while the question itself is being linearized."""
        from ..features import EMPTY
        previous, self._in_query = self._in_query, True
        try:
            return super().question(node, EMPTY if ctx is None else ctx)
        finally:
            self._in_query = previous
