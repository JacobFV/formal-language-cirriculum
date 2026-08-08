"""The Spanish pack: gender agreement, post-nominal adjectives, ¿inverted questions?

What this pack implements
-------------------------

* **Gender and number agreement.** Every noun carries its gender and plural in
  the vocabulary, and the article and every adjective in the phrase are inflected
  to match: ``un cubo rojo``, ``una esfera roja``, ``las esferas rojas``.
* **Adjectives follow the noun.** The realizer's default order is the English one,
  so :meth:`Spanish.noun_phrase` overrides it. This is the single most visible
  difference and getting it wrong makes every scene sentence read as translated
  English.
* **ser and estar.** ``ser`` for identity and classification (``o0 es un cubo``),
  ``estar`` for location and transient state (``la llave está en el ático``). The
  pack exposes both and the locative templates use ``estar``.
* **Inverted question marks.** ``¿`` opens every question, ``?`` closes it.
* **y/e and o/u.** ``y`` becomes ``e`` before a word starting with *i-* or *hi-*,
  and ``o`` becomes ``u`` before *o-* or *ho-*. A small rule, but its absence is
  exactly the kind of thing a native reader notices.
* **Plural formation** from the vocabulary, with the regular ``-s``/``-es`` rule
  for words the vocabulary does not have.

What it deliberately does not attempt
-------------------------------------

* **No subjunctive, no clitic pronouns, no agreement across a relative clause.**
  Nothing in the curriculum's structures needs them, and guessing would produce
  the confident-sounding errors this pack exists to avoid.
* **No ``el agua`` rule** for feminine nouns beginning with a stressed *a-*; no
  such noun is in the vocabulary, and the rule is only correct when it is.
* **Predicate heads the vocabulary does not translate** are rendered as a
  labelled row with the source identifier — ``adjudicated: 38, tamm, …`` — rather
  than as a guessed Spanish clause. That is a visible gap, on purpose: a labelled
  row is honest data, an invented verb is not.
"""

from __future__ import annotations

import re

from .base import Lexicon, NaturalLanguage
from .lexicon import load_vocabulary

__all__ = ["SPANISH", "Spanish"]

_VOCAB, _RAW = load_vocabulary("spanish")

# --------------------------------------------------------------------------
# closed class
# --------------------------------------------------------------------------
_OPERATORS = {
    "and": "y", "or": "o", "imp": "implica", "implies": "implica",
    "iff": "si y sólo si", "eq": "es igual a", "neq": "no es igual a",
    "entails": "implica", "supports": "apoya a", "attacks": "ataca a",
    "contradicts": "contradice a", "isa": "es un", "is_a": "es un",
    "add": "más", "sub": "menos", "mul": "por", "div": "dividido por",
    "mod": "módulo", "pow": "elevado a", "lt": "es menor que",
    "gt": "es mayor que", "le": "es como máximo", "ge": "es al menos",
    "requires": "requiere", "provides": "proporciona", "feeds": "alimenta a",
    "causes": "causa", "precedes": "precede a", "after": "después de",
}

_PREPOSITIONS = {
    "left_of": "a la izquierda de", "right_of": "a la derecha de",
    "above": "encima de", "below": "debajo de", "near": "cerca de",
    "inside": "dentro de", "front_of": "delante de", "behind": "detrás de",
    "on": "sobre", "at": "en",
}

_QUANTIFIERS = {"all": "todos", "some": "algunos", "none": "ninguno",
                "exactly_two": "exactamente dos", "most": "la mayoría", "few": "pocos"}

_PREFIX_OPERATORS = {"not": "no", "neg": "no", "no": "no"}


# --------------------------------------------------------------------------
# templates that need agreement, and therefore the source words
# --------------------------------------------------------------------------
def _obj5(lang, terms):
    """``(obj o0 red cube 4 8)`` -> ``o0 es un cubo rojo situado en (4, 8)``."""
    oid, color, shape, x, y = (t.value for t in terms[:5])
    np = lang.noun_phrase(str(shape), adjectives=[str(color)], determiner="indef")
    # ser for what it is, estar for where it is; a past participle here would
    # have to agree with the noun's gender and adds nothing
    return f"{lang.text(oid)} es {np} y está en ({x}, {y})"


def _obj3(lang, terms):
    oid, color, shape = (t.value for t in terms[:3])
    return f"{lang.text(oid)} es {lang.noun_phrase(str(shape), adjectives=[str(color)], determiner='indef')}"


def _obj4(lang, terms):
    oid, color, x, y = (t.value for t in terms[:4])
    return f"{lang.text(oid)} es {lang.adjective(str(color))} y está en ({x}, {y})"


def _color2(lang, terms):
    oid, color = (t.value for t in terms[:2])
    return f"{lang.text(oid)} es {lang.adjective(str(color))}"


def _shape2(lang, terms):
    oid, shape = (t.value for t in terms[:2])
    return f"{lang.text(oid)} es {lang.noun_phrase(str(shape), determiner='indef')}"


def _fact2(lang, terms):
    kind, who = (t.value for t in terms[:2])
    return f"{lang.text(who)} es {lang.noun_phrase(str(kind), determiner='indef')}"


def _isa2(lang, terms):
    a, b = (t.value for t in terms[:2])
    return f"{lang.text(a)} es {lang.noun_phrase(str(b), determiner='indef')}"


def _spatial(word):
    def _rel(lang, terms):
        color, shape = (t.value for t in terms[:2])
        return f"{word} {lang.noun_phrase(str(shape), adjectives=[str(color)], determiner='def')}"
    return _rel


_PREDICATE_TEMPLATES = {
    "obj/5": _obj5, "obj/4": _obj4, "obj/3": _obj3,
    "color/2": _color2, "shape/2": _shape2,
    "fact/2": _fact2, "isa/2": _isa2, "inst/2": _isa2, "entity/2": _isa2,
    "left_of/2": _spatial("a la izquierda de"),
    "right_of/2": _spatial("a la derecha de"),
    "above/2": _spatial("encima de"), "below/2": _spatial("debajo de"),
    "ex/2": "{0} → {1}",
    "rule/2": "{0} implica {1}",
    "rule/3": "regla {0}: {1} si {2}",
    "means/2": "{0} significa {1}",
    "says/2": "{0} dice {1}",
    "claims/2": "{0} afirma que {1}",
    "bind/2": "{0} está ligado a {1}",
    "at/1": "posición {0}",
    "leaf/1": "hoja {0}",
    "step/4": "paso {0}: {1} {2} {3}",
    "step/3": "paso {0}: {1} {2}",
    "observed/2": "se observó que {0} es {1}",
    "predicts/3": "{0} predice {2} para {1}",
    "predicts/2": "{0} predice {1}",
    "vote/3": "en la ronda {0}, {1} votó {2}",
    "cost/2": "{0} cuesta {1}",
    "bits/2": "{0} ocupa {1} bits",
    "value/2": "{0} tiene el valor {1}",
    "set/2": "{0} se fija en {1}",
    "has/2": "{0} tiene {1}",
    "prop/2": "{0} es {1}",
    "type/1": "tipo {0}",
    "candidate/2": "{0}: {1}",
    "candidate/1": "{0}",
    "claim/1": "{0}",
    "claim/3": "{0}: {1} causa {2}",
    "macro/2": "{0} abrevia {1}",
    "coalition/2": "la coalición {0} vale {1}",
    "event/3": "{0} va de {1} a {2}",
    "give/3": "{0} da {2} a {1}",
    "word/2": "{0} aparece {1} veces",
    "formula/2": "{0}: {1}",
    "theory/2": "{0}: {1}",
    "quant/2": "{0} de ellos son {1}",
    "parent/2": "{0} es progenitor de {1}",
    "adjudicated/4": "ensayo {0}: {1} sobre {2} fue {3}",
    "obs/3": "en el bloque {0}, {1} = {2}",
    "do/3": "en el bloque {0}, fijar {1} en {2}",
    "after/4": "bloque {0}, ejecución {1}: {2} = {3}",
    "item/4": "{0}: {1}, {2}, {3}",
    "input/3": "caso {0}, posición {1}: {2}",
    "output/3": "caso {0}, posición {1}: {2}",
    "turn/3": "turno {0}: {1} {2}",
    "dim/4": "{0} tiene dimensiones ({1}, {2}, {3})",
    "needs/3": "{0} necesita {1} = {2}",
    "norm/5": "{0} (prioridad {1}): si {2} entonces {3} {4}",
    "kb_rule/3": "{0} registra que {1} implica {2}",
    "kb_fact/3": "{0} registra que {1} es {2}",
    "apply/2": "apply({0}, {1})",
    "at_start/1": "{0} al principio",
    "at_end/1": "{0} al final",
    "color/1": "de color {0}",
    "shape/1": "de forma {0}",
    "resolve_by/1": "resolver por {0}",
    "schema/2": "{0}: {1}",
    "equation/2": "{0}: {1}",
}


def _quant(lang, terms):
    """One construction per quantifier: Spanish will not take a single frame.

    ``todos los objetos`` but ``algún objeto``; ``ningún`` negates the verb.
    The adjective agrees with whichever noun the frame chose.
    """
    q, what = (t.value for t in terms[:2])
    sg = lang.adjective(str(what))
    pl = lang.adjective(str(what), plural=True)
    return {
        "all": f"¿son {pl} todos los objetos?",
        "some": f"¿hay algún objeto {sg}?",
        "none": f"¿no hay ningún objeto {sg}?",
        "exactly_two": f"¿hay exactamente dos objetos {pl}?",
    }.get(str(q), f"¿hay objetos {pl}?")


def _q_which(lang, terms):
    color, shape = (t.value for t in terms[:2])
    return f"¿qué objeto es {lang.noun_phrase(str(shape), adjectives=[str(color)], determiner='def')}?"


def _q_the(lang, terms):
    color = terms[0].value
    rest = lang.clause(terms[1]) if len(terms) > 1 else ""
    return f"busca el objeto {lang.adjective(str(color))} {rest}.".replace("  ", " ")


def _q_who(lang, terms):
    """``who(floats)`` — the argument is a verb and has to be finite."""
    key = str(terms[0].value)
    verb = lang.lexicon.vocabulary.verbs.get(key)
    return f"¿quién {verb.finite() if verb else lang.clause(terms[0])}?"


_QUERY_TEMPLATES = {
    "which": _q_which,
    "the": _q_the,
    "who": _q_who,
    "which_color": "¿qué color significa {0}?",
    "classify": "¿{0} es alto o bajo?",
    "at": "¿qué símbolo está en la posición {0}?",
    "accept": "¿la cadena {0} pertenece al lenguaje?",
    "balanced": "¿está equilibrada la cadena?",
    "palindrome": "¿es la cadena un palíndromo?",
    "max_depth": "¿cuál es la profundidad máxima de anidamiento?",
    "first_leaf": "¿cuál es la primera hoja del árbol?",
    "next": "¿qué viene a continuación?",
    "quant": _quant,
    "find": "busca el objeto {0}.",
    "value_of": "¿a qué está ligado {0}?",
    "unify": "¿con qué unifica {0}?",
    "holds": "¿se cumple {0} de {1}?",
    "answer": "¿cuál es la respuesta?",
    "how_many": "¿cuántos {0} hay?",
    "resolve_query_in": "responde la pregunta de la mitad {0}.",
}

SPANISH = Lexicon(
    definite="el", definite_f="la", definite_pl="los", definite_fpl="las",
    indefinite="un", indefinite_f="una",
    copula_sg="es", copula_pl="son",
    negation="no", conjunction="y", disjunction="o", yes="sí", no="no", of="de",
    question_open="¿", question_mark="?",
    operators=_OPERATORS, prepositions=_PREPOSITIONS, quantifiers=_QUANTIFIERS,
    prefix_operators=_PREFIX_OPERATORS,
    field_intros=dict(_RAW.get("field_intros") or {}),
    predicate_words=dict(_RAW.get("predicate_words") or {}),
    predicate_templates={**{k: v for k, v in (_RAW.get("predicate_templates") or {}).items()},
                         **_PREDICATE_TEMPLATES},
    query_templates={**{k: v for k, v in (_RAW.get("query_templates") or {}).items()},
                     **_QUERY_TEMPLATES},
    instruction="Responde exactamente con una de estas opciones: {choices}\n"
                "Responde sólo con la respuesta.",
    instruction_many="Responde exactamente con una de las {n} opciones anteriores.\n"
                     "Responde sólo con la respuesta.",
    options_heading="Opciones:",
    pronouns={"f": "ella", "m": "él"},
    name_gender={"alice": "f", "bob": "m", "carol": "f",
                 "dave": "m", "erin": "f", "frank": "m"},
    vocabulary=_VOCAB,
)

#: ``ser`` for identity, ``estar`` for location and transient state
_ESTAR_SG, _ESTAR_PL = "está", "están"

#: Feminine nouns beginning with a **stressed** /a/ take ``el``/``un`` in the
#: singular — ``el agua fría``, not ``la agua fría`` — while their adjectives
#: still agree as feminine. The rule is only correct for stressed initials, so
#: it is an explicit list rather than a prefix match: ``la arcilla`` and ``la
#: acción`` are unstressed and take ``la``.
_EL_AGUA = frozenset({
    "agua", "área", "arma", "aula", "alma", "hambre", "águila", "ala",
    "acta", "hacha", "ancla", "aria", "asa", "hada",
})
_I_INITIAL = re.compile(r"^(i|hi)(?!e)", re.I)
_O_INITIAL = re.compile(r"^(o|ho)", re.I)


class Spanish(NaturalLanguage):
    """Spanish prose."""

    grammar_notes = (
        "gender and number agreement on articles and adjectives",
        "adjectives follow the noun",
        "ser for identity, estar for location and state",
        "inverted opening question mark",
        "y/e and o/u before i- and o-",
        "plural from the vocabulary, regular -s/-es otherwise",
    )

    def __init__(self):
        super().__init__(
            code="spanish", name="Spanish", lexicon=SPANISH,
            description="Spanish prose with gender agreement and post-nominal adjectives.")

    # ---- morphology ---------------------------------------------------
    def determiner(self, kind, *, gender="m", plural=False, word=""):
        """The article — with the ``el agua`` exception for stressed initial /a/."""
        if gender == "f" and not plural and word.lower() in _EL_AGUA:
            gender = "m"
        return super().determiner(kind, gender=gender, plural=plural, word=word)

    def pluralize(self, word: str) -> str:
        """Regular Spanish plural, for a word the vocabulary does not carry."""
        if not word:
            return word
        if word[-1] in "aeiou":
            return word + "s"
        if word.endswith("z"):
            return word[:-1] + "ces"
        return word + "es"

    def noun_phrase(self, noun_key, *, adjectives=(), determiner=None,
                    count=None, plural=False):
        """Determiner, noun, then adjectives — with everything agreeing."""
        noun = self.lexicon.vocabulary.nouns.get(noun_key)
        if noun is not None:
            head = noun.plural if (plural and noun.plural) else noun.lemma
            if plural and not noun.plural:
                head = self.pluralize(noun.lemma)
            gender = noun.gender or "m"
        else:
            head = self.word(noun_key)
            head = self.pluralize(head) if plural else head
            gender = "m"
        adjs = [self.adjective(a, gender=gender, plural=plural) for a in adjectives]
        det = "" if determiner is None else self.determiner(
            determiner, gender=gender, plural=plural, word=head)
        return self.join_words([str(count) if count is not None else "", det, head, *adjs])

    # ---- syntax -------------------------------------------------------
    def join_list(self, items):
        """``a, b y c`` — with ``y`` becoming ``e`` before *i-* or *hi-*."""
        items = [i for i in items if i]
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        conj = "e" if _I_INITIAL.match(items[-1]) else "y"
        return f"{self.lexicon.list_separator.join(items[:-1])} {conj} {items[-1]}"

    def disjoin(self, items):
        items = [i for i in items if i]
        conj = "u" if items and _O_INITIAL.match(items[-1]) else "o"
        return f" {conj} ".join(items)

    def locative(self, entity: str, place: str, *, plural: bool = False) -> str:
        """Location takes ``estar``, never ``ser``."""
        return self.join_words([entity, _ESTAR_PL if plural else _ESTAR_SG, place])

    _TRAILING = (" de", " a", " para", " en", " con", " que")

    def clean_label(self, label):
        """Drop a trailing preposition: it needs a complement that is not there."""
        for tail in self._TRAILING:
            if label.endswith(tail):
                return label[: -len(tail)]
        return label

    def labelled(self, label, value):
        """A single value under a label is a data row, not a sentence."""
        return f"{self.clean_label(label)}{self.lexicon.colon} {value}"

    def bullet_heading(self, name):
        return f"{name.replace('_', ' ')}{self.lexicon.colon}"

    def field_sentence(self, name, body, *, is_list, intro):
        if intro:
            return self.sentence(self.join_words([intro, body]))
        # no authored lead-in: a labelled row, rather than a guessed article
        return self.sentence(f"{name.replace('_', ' ')}{self.lexicon.colon} {body}")

    def generic_question(self, head, args):
        """No template for this question: ask for the value by name.

        The head stays in its source form because inventing a Spanish noun for
        an untranslated predicate is exactly the kind of confident error this
        pack refuses to make.
        """
        joined = " ".join(a for a in args if a)
        words = self.lexicon.predicate_words.get(head)
        subject = self.clean_label(words) if words else f"«{head}»"
        return f"cuál es {subject}{f' para {joined}' if joined else ''}"

    def sentence(self, text, end=None):
        """Spanish opens a question as well as closing it."""
        out = super().sentence(text, end)
        if end == self.lexicon.question_mark and out and not out.startswith("¿"):
            out = "¿" + out
        return out

    def open_question(self, text):
        # the opening mark goes on in sentence(), after capitalization, so that
        # "¿Qué ...?" capitalizes the word and not the punctuation
        return text
