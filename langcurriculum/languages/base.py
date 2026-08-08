"""What a language pack is, and the realizer every natural one shares.

A **language pack** is the seam between what a lesson means and how it is said.
A lesson generator builds a structure and computes the answer from it; the pack
decides what the learner reads. Adding a language is therefore a matter of
supplying words and rules, not of touching 180 generators.

A pack is three things:

:class:`~langcurriculum.languages.lexicon.Vocabulary`
    the open class — nouns with the gender, plural and measure word their
    language needs, adjectives in every form it distinguishes, verbs, names.
    Loaded from JSON that ships with the package.

:class:`Lexicon`
    the closed class and the typography — articles, copula, negation,
    conjunctions, quantifiers, operator and relational words, punctuation, and
    whether words are separated by spaces at all — plus the per-field lead-ins
    and per-structure templates that make a common shape read naturally.

:class:`NaturalLanguage`
    the realizer. It walks the structure once and, at every point where
    languages differ, calls a **strategy method** rather than deciding for
    itself. The strategies are the interesting part of this module:

    ==========================  =====================================================
    strategy                    what a pack decides by overriding it
    ==========================  =====================================================
    :meth:`~NaturalLanguage.noun_phrase`      determiner and adjective order, agreement, measure words
    :meth:`~NaturalLanguage.relational`       word order in ``X relates-to Y``
    :meth:`~NaturalLanguage.attributive`      how ``X is Y`` is built
    :meth:`~NaturalLanguage.labelled`         a label attached to one value
    :meth:`~NaturalLanguage.enumerated`       a label attached to several
    :meth:`~NaturalLanguage.field_sentence`   how a section of the episode is introduced
    :meth:`~NaturalLanguage.question`         question formation — fronting, particle, or neither
    :meth:`~NaturalLanguage.join_words`       whether words are separated at all
    :meth:`~NaturalLanguage.join_list`        list coordination
    :meth:`~NaturalLanguage.sentence`         capitalization and terminal punctuation
    ==========================  =====================================================

    Nothing in the walk assumes SVO order, suffix pluralization, article
    selection by phonology, or questions formed by inversion. Those are all
    English answers to questions the strategies ask.

Templates may be strings — positional over already-rendered arguments — or
callables ``fn(language, terms) -> str | None`` when a phrase needs the source
words rather than their rendering, which is what agreement requires. Returning
``None`` falls through to the generic rules.

To add a language, see :mod:`langcurriculum.languages.spanish` for one with
inflection and :mod:`langcurriculum.languages.chinese` for one without.
"""

from __future__ import annotations

import re
import string as _string
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .._structure import PRIMITIVE_TYPES, Term
from .lexicon import Vocabulary

__all__ = ["Lexicon", "Language", "NaturalLanguage", "FormalLanguage"]

@dataclass(frozen=True)
class Lexicon:
    """The closed class and the typography, separated from the walk that uses them."""

    # ---- closed class -------------------------------------------------
    definite: str = "the"
    definite_f: str = ""
    definite_pl: str = ""
    definite_fpl: str = ""
    indefinite: str = "a"
    indefinite_f: str = ""
    indefinite_before_vowel: str = ""
    copula_sg: str = "is"
    copula_pl: str = "are"
    negation: str = "not"
    conjunction: str = "and"
    disjunction: str = "or"
    yes: str = "yes"
    no: str = "no"
    of: str = "of"

    # ---- typography ---------------------------------------------------
    #: what separates words. Empty for scripts written without spacing.
    word_joiner: str = " "
    #: whether a sentence starts with a capital letter
    capitalizes: bool = True
    full_stop: str = "."
    question_mark: str = "?"
    #: opening question mark, for languages that use one
    question_open: str = ""
    list_separator: str = ", "
    clause_separator: str = "; "
    #: separator inside a Latin function application, which stays half-width
    #: even in a script that is otherwise full-width: ``t(a, b, c)``
    arg_separator: str = ", "
    colon: str = ":"
    bullet: str = "  - "

    # ---- relational and operator words --------------------------------
    operators: Mapping[str, str] = field(default_factory=dict)
    prepositions: Mapping[str, str] = field(default_factory=dict)
    quantifiers: Mapping[str, str] = field(default_factory=dict)
    prefix_operators: Mapping[str, str] = field(default_factory=dict)

    # ---- framing ------------------------------------------------------
    field_intros: Mapping[str, str] = field(default_factory=dict)
    predicate_templates: Mapping[str, Any] = field(default_factory=dict)
    query_templates: Mapping[str, Any] = field(default_factory=dict)
    #: predicate head -> the words that realize it between two arguments
    predicate_words: Mapping[str, str] = field(default_factory=dict)
    instruction: str = "Answer with exactly one of: {choices}\nReply with the answer only."
    instruction_many: str = ("Answer with exactly one of the {n} options listed above.\n"
                             "Reply with the answer only.")
    options_heading: str = "Options:"

    # ---- open class, for the lessons that are about morphology --------
    verbs: Sequence[str] = ()
    intransitive_verbs: Sequence[str] = ()
    adverbs: Sequence[str] = ()
    noun_forms: Sequence[tuple[str, str]] = ()
    agreement_forms: Sequence[tuple[str, str]] = ()
    pronouns: Mapping[str, str] = field(default_factory=dict)
    name_gender: Mapping[str, str] = field(default_factory=dict)
    preposition_words: Sequence[str] = ()

    # ---- the open-class vocabulary ------------------------------------
    vocabulary: Vocabulary = field(default_factory=Vocabulary)

    # ---- held-out vocabulary -----------------------------------------
    synonyms: Mapping[str, str] = field(default_factory=dict)

    # ---- helpers a pack may override ----------------------------------
    def copula(self, plural: bool = False) -> str:
        return self.copula_pl if plural else self.copula_sg

    def word_for(self, head: str) -> str:
        """A head symbol as words: ``left_of`` -> ``to the left of``."""
        return (self.predicate_words.get(head)
                or self.operators.get(head)
                or self.prepositions.get(head)
                or head.replace("_", " "))


class Language:
    """Base class. A language turns a structure into the text a learner reads."""

    code: str = ""
    name: str = ""
    kind: str = "natural"
    description: str = ""
    #: what the pack claims to realize, and what it leaves as a labelled row
    grammar_notes: tuple[str, ...] = ()
    lexicon: Lexicon = Lexicon()

    def render(self, term: Term) -> str:            # pragma: no cover - abstract
        raise NotImplementedError

    def token(self, value: str) -> str:
        """Render one answer token — an option, or the gold answer.

        The options have to be in the same language as the prompt. If the scene
        says ``rojo`` and the option list says ``red``, the task has quietly
        become "translate, then answer", which is a different and much harder
        lesson than the one being scored. Words the pack does not know — object
        ids, nonce forms, numbers — pass through, which is most of them.
        """
        return value

    def prompt(self, observation: str, choices: Sequence[str], *, max_inline: int = 40) -> str:
        """Assemble what an agent is handed: the episode, then the answer set."""
        lex = self.lexicon
        opts = [str(c) for c in choices]
        if len(opts) <= max_inline:
            tail = lex.instruction.format(choices=" | ".join(opts))
        else:
            listed = "\n".join(f"{lex.bullet}{o}" for o in opts)
            tail = f"{lex.options_heading}\n{listed}\n" + lex.instruction_many.format(n=len(opts))
        return f"{observation}\n\n{tail}"

    def info(self) -> dict[str, Any]:
        return {"code": self.code, "name": self.name, "kind": self.kind,
                "description": self.description,
                "vocabulary": self.lexicon.vocabulary.counts(),
                "grammar": list(self.grammar_notes)}

    def __repr__(self) -> str:
        return f"<Language {self.code} ({self.kind})>"


class FormalLanguage(Language):
    """A notation rather than a prose language."""

    kind = "formal"


def _slots_used(template: str) -> int:
    """How many positional slots a format string actually consumes."""
    used = -1
    for _, fieldname, _, _ in _string.Formatter().parse(template):
        if fieldname is None or not fieldname.isdigit():
            continue
        used = max(used, int(fieldname))
    return used + 1


_SENTENCE_END = re.compile(r"[.!?。？！]$")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([?.!,;:])")


class NaturalLanguage(Language):
    """The shared realizer. Every point where languages differ is a strategy."""

    kind = "natural"
    #: where :attr:`Lexicon.synonyms` applies: ``none``, ``query`` or ``all``
    synonym_scope: str = "none"
    #: a list field with more than this many items becomes bullets
    bullet_threshold: int = 4
    _in_query: bool = False

    def __init__(self, *, code: str, name: str, lexicon: Lexicon,
                 description: str = "", synonym_scope: str | None = None,
                 grammar_notes: Sequence[str] = ()):
        self.code = code
        self.name = name
        self.lexicon = lexicon
        self.description = description
        if grammar_notes:
            self.grammar_notes = tuple(grammar_notes)
        if synonym_scope is not None:
            self.synonym_scope = synonym_scope

    # ==================================================================
    # strategies: everything a language decides differently
    # ==================================================================
    def join_words(self, parts: Sequence[str]) -> str:
        """Put words together. Not every script separates them."""
        return self.lexicon.word_joiner.join(p for p in parts if p)

    def join_clauses(self, items: Sequence[str]) -> str:
        """Coordinate whole clauses, which is not always how items are joined.

        English coordinates clauses much as it coordinates nouns, so the default
        defers to :meth:`join_list`. Chinese does not: its enumerating comma is
        for items, and running clauses together with it reads wrong.
        """
        return self.join_list(items)

    def join_list(self, items: Sequence[str]) -> str:
        """List coordination: ``a``, ``a and b``, ``a, b and c``."""
        lex = self.lexicon
        items = [i for i in items if i]
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        return self.join_words([lex.list_separator.join(items[:-1]), lex.conjunction, items[-1]])

    def determiner(self, kind: str, *, gender: str = "m", plural: bool = False,
                   word: str = "") -> str:
        """The article for a noun. Languages without articles return ``""``."""
        lex = self.lexicon
        if kind == "def":
            if plural:
                return (lex.definite_fpl if gender == "f" else lex.definite_pl) or lex.definite
            return (lex.definite_f if gender == "f" else lex.definite) or lex.definite
        if kind == "indef":
            return (lex.indefinite_f if gender == "f" else lex.indefinite) or lex.indefinite
        return ""

    def noun_phrase(self, noun_key: str, *, adjectives: Sequence[str] = (),
                    determiner: str | None = None, count: int | str | None = None,
                    plural: bool = False) -> str:
        """Build a noun phrase.

        The English shape — determiner, adjectives, noun — is the *default*, not
        an assumption: a pack that puts adjectives after the noun, agrees them
        with its gender, or requires a measure word overrides this whole method.
        """
        lex = self.lexicon
        noun = lex.vocabulary.nouns.get(noun_key)
        head = noun.form(plural=plural) if noun else self.word(noun_key)
        gender = noun.gender if noun else "m"
        adjs = [self.adjective(a, gender=gender, plural=plural) for a in adjectives]
        det = "" if determiner is None else self.determiner(
            determiner, gender=gender, plural=plural, word=(adjs[0] if adjs else head))
        parts = [str(count) if count is not None else "", det, *adjs, head]
        return self.join_words([p for p in parts if p])

    def adjective(self, key: str, *, gender: str = "m", plural: bool = False) -> str:
        adj = self.lexicon.vocabulary.adjectives.get(key)
        return adj.agree(gender, plural=plural) if adj else self.word(key)

    def relational(self, subject: str, relation: str, obj: str) -> str:
        """``X relates-to Y``. Subject-first is English's answer, not a law."""
        return self.join_words([subject, relation, obj])

    def attributive(self, entity: str, attribute: str) -> str:
        """``X is Y``."""
        return self.join_words([entity, self.lexicon.copula_sg, attribute])

    def clean_label(self, label: str) -> str:
        """Strip the parts of a relational phrase that only work between two arguments.

        ``predicate_words`` are authored to sit *between* a subject and an
        object. Used as a label over a single value they can leave a dangling
        particle or copula — Chinese ``的实体是`` in front of nothing, Spanish
        ``el estado de`` with no complement — so a pack trims them here.
        """
        return label

    def labelled(self, label: str, value: str) -> str:
        """A label attached to one value: ``weight 3``."""
        return self.join_words([self.clean_label(label), value])

    def enumerated(self, label: str, values: Sequence[str]) -> str:
        """A label attached to several: ``rule: a, b and c``."""
        return self.join_words([self.clean_label(label) + self.lexicon.colon,
                                self.join_list(values)])

    def bullet_heading(self, name: str) -> str:
        """The heading over a bulleted section, when the pack has no lead-in."""
        lex = self.lexicon
        return self.join_words([lex.definite, name.replace("_", " ")]) + lex.colon

    def field_sentence(self, name: str, body: str, *, is_list: bool, intro: str | None) -> str:
        """Introduce a section of the episode."""
        lex = self.lexicon
        if intro:
            return self.sentence(self.join_words([intro, body]))
        words = name.replace("_", " ")
        if is_list:
            return self.sentence(self.join_words([f"{lex.definite} {words}{lex.colon}", body]))
        return self.sentence(self.join_words([lex.definite, words, lex.copula_sg, body]))

    def capitalize(self, text: str) -> str:
        """Capitalize the first *letter*, in scripts that have case.

        The first letter, not the first character: a sentence may open with a
        quotation mark or an inverted question mark.
        """
        if not self.lexicon.capitalizes:
            return text
        for i, ch in enumerate(text):
            if ch.isalpha():
                return text[:i] + ch.upper() + text[i + 1:]
        return text

    def sentence(self, text: str, end: str | None = None) -> str:
        """Normalize spacing, capitalize where the script does, and punctuate."""
        text = " ".join(text.split()) if self.lexicon.word_joiner else text.strip()
        text = _SPACE_BEFORE_PUNCT.sub(r"\1", text).strip()
        if not text:
            return ""
        text = self.capitalize(text)
        if end == "":
            return text
        end = self.lexicon.full_stop if end is None else end
        return text if _SENTENCE_END.search(text) else text + end

    # ==================================================================
    # the walk
    # ==================================================================
    def render(self, term: Term) -> str:
        if term.type != "record":
            return self.sentence(self.clause(term))
        fields = [(k, v) for k, v in term.value]
        query = None
        blocks: list[str] = []
        for name, value in fields:
            if name in ("query", "utterance") and query is None:
                query = (name, value)
                continue
            blocks.append(self.field_block(name, value))
        if query is not None:
            blocks.append(self.question(query[1]) if query[0] == "query"
                          else self.sentence(self.clause(query[1]), end=""))
        return "\n".join(b for b in blocks if b)

    def field_block(self, name: str, value: Term) -> str:
        lex = self.lexicon
        intro = lex.field_intros.get(name)
        items = list(value.children) if value.type == "list" else None
        if items is not None:
            if not items:
                return self.field_sentence(name, self.word("empty"), is_list=False, intro=intro)
            rendered = [self.clause(x) for x in items]
            # a lead-in authored for a single value ("The goal is") in front of a
            # list needs its colon, or the list runs into the phrase
            if intro and not intro.rstrip().endswith(lex.colon):
                intro = intro.rstrip() + lex.colon
            if len(rendered) > self.bullet_threshold or any(len(r) > 64 for r in rendered):
                head = intro or self.bullet_heading(name)
                return (self.capitalize(head.rstrip()) + "\n"
                        + "\n".join(f"{lex.bullet}{r}" for r in rendered))
            if any((lex.list_separator.strip() in r) or (lex.colon in r) for r in rendered):
                body = lex.clause_separator.join(rendered)
            elif all(x.type in PRIMITIVE_TYPES for x in items):
                body = self.join_list(rendered)
            else:
                body = self.join_clauses(rendered)
            return self.field_sentence(name, body, is_list=True, intro=intro)
        return self.field_sentence(name, self.clause(value), is_list=False, intro=intro)

    # ---- clauses ------------------------------------------------------
    def clause(self, term: Term, *, top: bool = False) -> str:
        lex = self.lexicon
        if term.type in ("ident", "token", "str", "num"):
            return self.text(term.value)
        if term.type == "nil":
            return self.word("nothing")
        if term.type == "list":
            inner = [self.clause(x) for x in term.children]
            if not inner:
                return self.word("nothing")
            return self.join_list(inner) if top else f"({lex.list_separator.join(inner)})"
        if term.type == "tuple":
            return "(" + lex.arg_separator.join(self.clause(x) for x in term.children) + ")"
        if term.type == "record":
            return lex.clause_separator.join(
                self.attributive(k.replace("_", " "), self.clause(v)) for k, v in term.value)
        if term.type == "app":
            fn, *kvs = term.value
            inner = lex.arg_separator.join(f"{k}={self.clause(v)}" for k, v in kvs)
            return f"{fn}({inner})"
        if term.type in ("pred", "rel", "node"):
            return self.predicate(term)
        return self.text(term.value)

    def predicate(self, term: Term) -> str:
        lex = self.lexicon
        head, *rest = term.value
        terms = [a for a in rest if isinstance(a, Term)]
        out = self._apply_template(lex.predicate_templates, str(head), terms, arity=len(terms))
        if out is not None:
            return out
        args = [self.clause(a) for a in terms]
        if str(head) in lex.prefix_operators and len(args) == 1:
            return self.join_words([lex.prefix_operators[str(head)], args[0]])
        if not args:
            return lex.word_for(str(head))
        if len(str(head)) <= 2 and str(head) not in lex.operators:
            return f"{head}({lex.arg_separator.join(args)})"    # function application
        if len(args) == 1:
            return self.labelled(lex.word_for(str(head)), args[0])
        if len(args) == 2:
            return self.relational(args[0], lex.word_for(str(head)), args[1])
        return self.enumerated(lex.word_for(str(head)), args)

    def _apply_template(self, table: Mapping[str, Any], head: str,
                        terms: Sequence[Term], *, arity: int | None = None,
                        require_all_args: bool = False) -> str | None:
        """Try ``head/arity`` then ``head``; strings format, callables are called.

        With ``require_all_args``, a template that has fewer slots than the
        structure has arguments is **rejected** rather than used. That case is a
        template defect: it silently asks a question about less than it was
        given, which is not a wording problem but a different, easier question.
        Falling through to the generic form is clunkier and correct, and it
        means a pack cannot lose information by being written in a hurry.
        """
        for key in ((f"{head}/{arity}", head) if arity is not None else (head,)):
            tpl = table.get(key)
            if tpl is None:
                continue
            if callable(tpl):
                out = tpl(self, terms)
                if out is not None:
                    return out.strip()
                continue
            if require_all_args and _slots_used(tpl) < len(terms):
                continue
            args = [self.clause(a) for a in terms]
            try:
                return tpl.format(*(args + [""] * 8)).strip()
            except (IndexError, KeyError):
                continue
        return None

    # ---- the question -------------------------------------------------
    def query_head(self, q: Term) -> str:
        return str(q.value[0] if q.type in ("pred", "rel", "node") and isinstance(q.value, tuple)
                   else q.value)

    def query_words(self, q: Term) -> list[str]:
        """One rendered string per argument of the query.

        A composite argument is *realized*, not flattened: reducing a query like
        ``select(and(not(color purple)), shape(sphere))`` to its leaf words drops
        the ``and`` and the ``not``, which asks something strictly easier than
        the episode poses. Atomic arguments come through as their own text.

        This is also where the held-out substitution applies, so the question can
        name a colour the learner has never read while the body of the episode
        keeps the word it was trained on.
        """
        prev, self._in_query = self._in_query, True
        try:
            return [self.text(c.value) if c.type in PRIMITIVE_TYPES else self.clause(c)
                    for c in q.children]
        finally:
            self._in_query = prev

    def question(self, q: Term) -> str:
        """Form a question. Fronting, a particle, or neither — the pack decides."""
        text, templated = self.question_text(q)
        lex = self.lexicon
        if templated and _SENTENCE_END.search(text.strip()):
            return self.sentence(text, end="")
        return self.sentence(self.open_question(text), end=lex.question_mark)

    def open_question(self, text: str) -> str:
        """Hook for languages that mark a question at the front as well as the end."""
        return self.lexicon.question_open + text if self.lexicon.question_open else text

    def question_text(self, q: Term) -> tuple[str, bool]:
        """``(text, came_from_a_template)``."""
        head = self.query_head(q)
        prev, self._in_query = self._in_query, True
        try:
            out = self._apply_template(self.lexicon.query_templates, head,
                                       list(q.children), require_all_args=True)
        finally:
            self._in_query = prev
        if out is not None:
            return out, True
        return self.generic_question(head, self.query_words(q)), False

    def generic_question(self, head: str, args: Sequence[str]) -> str:
        """The fallback when no template names this question."""
        return self.join_words([head.replace("_", " "), *args])

    # ---- leaves -------------------------------------------------------
    def atoms(self, term: Term) -> list[str]:
        """The leaf words under a term, in order."""
        out: list[str] = []
        stack = [term]
        while stack:
            t = stack.pop(0)
            if t.type in PRIMITIVE_TYPES and not t.children:
                out.append(self.text(t.value))
            else:
                stack = list(t.children) + stack
        return out

    def word(self, key: str) -> str:
        """One open-class word in this language, or the key if it is not ours."""
        return self.lexicon.vocabulary.translate(key)

    def token(self, value: str) -> str:
        return self.lexicon.vocabulary.translate(value) if isinstance(value, str) else value

    def text(self, value: Any) -> str:
        s = value if isinstance(value, str) else str(value)
        if not isinstance(value, str):
            return s
        if self.synonym_scope == "all" or (self.synonym_scope == "query" and self._in_query):
            s = self.lexicon.synonyms.get(s, s)
        return self.lexicon.vocabulary.translate(s)
