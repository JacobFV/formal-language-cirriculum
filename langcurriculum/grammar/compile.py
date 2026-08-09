"""Compiling the curriculum's structures into abstract syntax.

:class:`~langcurriculum._structure.Term` is what 170 lesson generators build. It
is a semantic structure — it records what the episode is *about*, and it was
designed so that a generator could compute the right answer over a tree rather
than over a string. That was the right decision and it is why this rewrite is
possible at all: the meaning was never entangled with the English.

What ``Term`` is not is a syntax tree. It has no notion of a noun phrase, no
roles, no features. This module supplies those, using the frame lexicon in
:mod:`~langcurriculum.grammar.frames`, and hands the result to a grammar.

One decision worth stating
--------------------------

Deciding whether ``cube`` is a *word* or a *symbol* cannot be left to each
grammar, because then the same episode would have different structure in
different languages and the curriculum's central invariant — that the same
option is correct in every language — would quietly depend on the vocabulary a
pack happened to ship.

So the decision is made once, here, against the **English** vocabulary, on the
grounds that English is what the generators coin their constants in. If English
knows ``cube`` as a noun, it is a noun in the abstract syntax, and a grammar
that lacks the word renders it as the bare lemma. If English does not know
``o0``, it is a symbol everywhere, and no grammar will inflect or translate it.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Sequence

from .._structure import PRIMITIVE_TYPES, Term
from .category import (
    ADV, AGENT, ATTRIBUTE, INDEX, LOCATION, N, PATIENT, RECIPIENT, SOURCE,
    THEME, V, VALUE,
)
from .features import EMPTY, FS
from .frames import REPORTING, SPATIAL_FRAME, Frame, frame_for
from .syntax import (
    Arg, Node, adj, coord, cond, compare, enumerated, fn_app, indexed,
    labelled, lex, mapping, mk_ap, mk_cn, mk_np, negate, noun, pred_attr,
    pred_ident, pred_rel, pred_rel3, quant, sym, text_block, verb,
)

__all__ = ["compile_term", "compile_episode", "compile_query", "classify",
           "curriculum_vocabulary"]


def curriculum_vocabulary() -> set[str]:
    """Every English word the curriculum's generators can actually coin.

    The union of the reference vocabulary and the predicate heads the lessons
    construct. A language that covers this set covers the curriculum; anything
    beyond it is headroom for a resource used outside these lessons.
    """
    from .frames import FRAMES
    vocab = _english()
    keys = set(vocab.nouns) | set(vocab.adjectives) | set(vocab.verbs)
    keys |= set(vocab.names) | set(vocab.words)
    keys |= {k.split("/")[0] for k in FRAMES}
    return {k for k in keys if k and k.isascii()}


def _english():
    """The reference vocabulary, loaded lazily to avoid an import cycle.

    English is the reference because it is what the generators coin their
    constants in — see the module docstring. Loaded straight from the data file
    rather than through a language object, so that deciding what counts as a
    word does not depend on any grammar being constructed first.
    """
    from ..languages.lexicon import load_vocabulary
    return load_vocabulary("english")[0]


_ADJ_LIKE = frozenset({"color", "shape", "size", "material"})


def classify(value: str) -> str:
    """``noun``, ``adj``, ``verb``, ``word`` or ``sym`` — decided once, against English.

    ``word`` is the category that was missing, and its absence was the single
    largest source of English in derived output. The reference vocabulary keeps
    a hundred and twenty-nine entries — *colour*, *yes*, *size*, *above*,
    *true*, *east* — outside the three inflecting classes, and everything in it
    was being treated as an opaque symbol. A symbol is never translated, so
    those words came out in English in all four hundred languages.

    They are translatable but not inflectable, which is why they are their own
    category rather than being folded into ``noun``: calling *above* a noun
    would send it to a noun paradigm and get it declined.
    """
    vocab = _english()
    if value in vocab.nouns:
        return "noun"
    if value in vocab.adjectives:
        return "adj"
    if value in vocab.verbs:
        return "verb"
    if value in vocab.words:
        return "word"
    if value in _curriculum_keys():
        # The curriculum's own key set is the last word on what counts as
        # vocabulary. ``leaf``, ``read``, ``book`` and ``left`` reach the page
        # from predicate heads and are absent from the reference vocabulary's
        # four tables, so they were symbols and stayed English — though every
        # language in the database translates them. A coined token is never in
        # this set, which is what makes consulting it safe.
        return "word"
    return "sym"


@lru_cache(maxsize=1)
def _curriculum_keys() -> frozenset[str]:
    """Curriculum keys that are not proper names, cached for the hot path."""
    return frozenset(curriculum_vocabulary() - set(_english().names))


def _leaf(value: Any) -> Node:
    """One primitive value as either a lexical item or an opaque symbol."""
    if not isinstance(value, str):
        return sym(value)
    if " " in value:
        return _word_sequence(value)
    kind = classify(value)
    if kind == "noun":
        return mk_np(mk_cn(noun(value)))
    if kind == "adj":
        return mk_ap(adj(value))
    if kind == "verb":
        return verb(value)
    if kind == "word":
        return lex(ADV, value)
    return sym(value)


def _word_sequence(value: str) -> Node:
    """A multi-word string: vocabulary if every token is, otherwise a symbol.

    Some generators build a whole sequence as one string — a few-shot lesson
    shows ``zrv nzrn ppk → green blue green``, where both sides are single
    ``str`` terms. As symbols neither was translated, and the second is ordinary
    vocabulary that every language in the database has.

    The test is **all or nothing**. ``green blue green`` is entirely words and
    translates; ``zrv nzrn ppk`` is entirely coined and must not be touched. A
    mixed string is left alone too, because the coined half of it is doing the
    work the lesson turns on and half-translating would obscure it.
    """
    tokens = value.split()
    if len(tokens) > 12 or any(classify(t) == "sym" for t in tokens):
        return sym(value)
    return lex(ADV, value)


def _as_np(value: Any, *, det: str = "", adjectives: Sequence[str] = ()) -> Node:
    """Build a noun phrase, or whatever the value actually is.

    A non-noun used to fall through to :func:`sym`, which meant that a bare
    colour — ``(obj o3 red 4 6)``, "o3 is red" — reached the page as the English
    word in every language. Anything that is vocabulary goes through
    :func:`_leaf` so that it is translated; only genuinely opaque tokens stay
    symbols.
    """
    mods = [adj(a) for a in adjectives if isinstance(a, str)]
    if isinstance(value, str) and classify(value) == "noun":
        return mk_np(mk_cn(noun(value), *mods), det=det or "bare")
    head = _leaf(value) if isinstance(value, str) else sym(value)
    return mk_np(mk_cn(head, *mods), det=det or "bare") if mods else head


def _str(term: Term | None) -> str:
    return "" if term is None else str(term.value)


# ======================================================================
# the compiler
# ======================================================================
def compile_term(term: Term) -> Node:
    """Turn one structure into one abstract syntax node."""
    if term.type in PRIMITIVE_TYPES and not term.children:
        return _leaf(term.value) if term.type != "nil" else sym("—")
    if term.type == "list":
        return coord("and", [compile_term(c) for c in term.children])
    if term.type == "tuple":
        return fn_app("", [compile_term(c) for c in term.children])
    if term.type == "app":
        head, *kvs = term.value
        return fn_app(str(head), [compile_term(v) for _, v in kvs])
    if term.type == "record":
        return coord("and", [compile_term(v) for _, v in term.value])
    if term.type in ("pred", "rel", "node"):
        return _compile_predicate(term)
    return sym(term.value)


def _compile_predicate(term: Term) -> Node:
    head, *rest = term.value
    args = [a for a in rest if isinstance(a, Term)]
    frame = frame_for(str(head), len(args))
    builder = _BUILDERS.get(frame.construction, _build_default)
    node = builder(str(head), frame, args)
    if str(head) in REPORTING:
        node = _mark_reported(node)
    if str(head) in SPATIAL_FRAME:
        node = node.but(frame="relative")
    return node


def _mark_reported(node: Node) -> Node:
    """Mark the complement of a reporting predicate as second-hand.

    Only the complement, not the whole clause: *Alice says the cube is red* is a
    direct observation **that Alice said something** and a report **about the
    cube**. Turkish marks those two clauses differently, and marking both the
    same way would be as wrong as marking neither.
    """
    from .category import PATIENT, VALUE
    marked = []
    for a in node.args:
        if a.role in (PATIENT, VALUE) and a.node.cat.name in ("Cl", "S"):
            marked.append(Arg(a.role, a.node.but(evid="reported")))
        else:
            marked.append(a)
    return Node(node.fn, node.cat, tuple(marked), node.feats,
                node.lemma, node.text)


# ---- one builder per construction ------------------------------------
def _label(head: str) -> Node:
    """A predicate head used as a row label — translatable, not an opaque token.

    ``leaf``, ``round``, ``example``, ``weight`` reach the page as labels, and
    as symbols they stayed English everywhere. A grammar that does not know the
    word still passes it through, so making them lexical costs nothing and
    recovers the ones that are ordinary vocabulary.
    """
    words = head.replace("_", " ")
    return lex(ADV, words)


def _build_default(head: str, frame: Frame, args: list[Term]) -> Node:
    return enumerated(_label(head), [compile_term(a) for a in args])


def _build_bare(head: str, frame: Frame, args: list[Term]) -> Node:
    return compile_term(args[0]) if args else _label(head)


def _build_labelled(head: str, frame: Frame, args: list[Term]) -> Node:
    if len(args) >= 2:
        return labelled(compile_term(args[0]), compile_term(args[1]))
    value = compile_term(args[0]) if args else sym("—")
    return labelled(_label(head), value)


def _build_enumerated(head: str, frame: Frame, args: list[Term]) -> Node:
    return enumerated(_label(head), [compile_term(a) for a in args])


def _build_pred_attr(head: str, frame: Frame, args: list[Term]) -> Node:
    return pred_attr(_as_np(args[0].value, det="def"), adj(_str(args[1])))


def _build_pred_ident(head: str, frame: Frame, args: list[Term]) -> Node:
    return pred_ident(_as_np(args[0].value, det="def"),
                      _as_np(args[1].value, det="indef"))


def _build_pred_ident_rev(head: str, frame: Frame, args: list[Term]) -> Node:
    """``(fact KIND WHO)`` says WHO is a KIND — the arguments arrive reversed."""
    return pred_ident(_as_np(args[1].value, det="def"),
                      _as_np(args[0].value, det="indef"))


def _build_obj_kind(head: str, frame: Frame, args: list[Term]) -> Node:
    """``(obj o0 yellow cube)`` — an identity clause with a modified predicate."""
    oid, colour, shape = args[0], args[1], args[2]
    return pred_ident(sym(oid.value),
                      _as_np(shape.value, det="indef", adjectives=[_str(colour)]))


def _build_obj_full(head: str, frame: Frame, args: list[Term]) -> Node:
    """``(obj o0 yellow cube 4 8)`` — the same, with a place adjunct."""
    oid = args[0]
    coords = [compile_term(a) for a in args[-2:]]
    place = fn_app("", coords)
    if len(args) >= 5:
        value = _as_np(args[2].value, det="indef", adjectives=[_str(args[1])])
    else:
        value = _as_np(args[1].value, det="indef")
    node = pred_ident(sym(oid.value), value)
    return Node(node.fn, node.cat, node.args + (Arg(LOCATION, place),), node.feats)


def _argument(term: Term) -> Node:
    """One argument of a relational predicate.

    A *composite* argument is a clause and must be compiled as one. Reaching
    past it to ``term.value`` — as this did — turns an embedded proposition into
    a noun phrase built from a raw tuple, which is both unreadable and, for the
    reported-speech lessons, wrong about what is being said.
    """
    if term.type in PRIMITIVE_TYPES and not term.children:
        return _as_np(term.value, det="def")
    return compile_term(term)


def _build_pred_rel(head: str, frame: Frame, args: list[Term]) -> Node:
    subject = _argument(args[0])
    obj = _argument(args[1]) if len(args) > 1 else sym("—")
    return pred_rel(subject, lex(V, head), obj)


def _build_pred_rel3(head: str, frame: Frame, args: list[Term]) -> Node:
    subject = _argument(args[0])
    theme = _argument(args[2]) if len(args) > 2 else sym("—")
    third = _argument(args[1]) if len(args) > 1 else sym("—")
    return pred_rel3(subject, lex(V, head), theme, third)


def _build_reports(head: str, frame: Frame, args: list[Term]) -> Node:
    """``(kb_fact K X Y)`` — a source reporting an embedded proposition."""
    inner = pred_attr(_as_np(args[1].value, det="def"), _leaf(args[2].value)) \
        if len(args) > 2 else sym("—")
    return pred_rel(compile_term(args[0]), lex(V, "records"), inner)


def _build_spatial(head: str, frame: Frame, args: list[Term]) -> Node:
    """A relation used as a modifier: *to the left of the red cube*."""
    target = _as_np(args[1].value, det="def", adjectives=[_str(args[0])]) \
        if len(args) > 1 else sym("—")
    return labelled(lex(V, frame.lemma or head), target)


def _build_indexed(head: str, frame: Frame, args: list[Term]) -> Node:
    rest = [compile_term(a) for a in args[1:]]
    body = rest[0] if len(rest) == 1 else enumerated(sym(""), rest)
    return indexed(compile_term(args[0]), body, kind=frame.kind or "step")


def _build_indexed_cond(head: str, frame: Frame, args: list[Term]) -> Node:
    inner = cond(compile_term(args[1]), compile_term(args[2])) if len(args) > 2 \
        else compile_term(args[1])
    return indexed(compile_term(args[0]), inner, kind=frame.kind or "rule")


def _build_mapping(head: str, frame: Frame, args: list[Term]) -> Node:
    return mapping(compile_term(args[0]), compile_term(args[1]))


def _build_coord(head: str, frame: Frame, args: list[Term]) -> Node:
    return coord(frame.lemma or "and", [compile_term(a) for a in args])


def _build_neg(head: str, frame: Frame, args: list[Term]) -> Node:
    return negate(compile_term(args[0])) if args else sym("—")


def _build_compare(head: str, frame: Frame, args: list[Term]) -> Node:
    return compare(compile_term(args[0]), frame.lemma or head, compile_term(args[1]))


def _build_quant(head: str, frame: Frame, args: list[Term]) -> Node:
    return quant(_str(args[0]), None, mk_ap(adj(_str(args[1]))))


def _build_nl_claim(head: str, frame: Frame, args: list[Term]) -> Node:
    """``(nl_claim all neg prism yellow)`` — *no prism is yellow*.

    The four parts a quantified claim is made of, kept apart so that each
    language can assemble them its own way. The generator used to do the
    assembling itself and hand over a finished English string, which is exactly
    the shape nothing downstream can translate.
    """
    quantifier, polarity, restriction, scope = (_str(a) for a in args[:4])
    node = quant(quantifier,
                 _as_np(restriction, det="bare"),
                 mk_ap(adj(scope)))
    return node.but(pol=polarity)


def _build_nl_transitive(head: str, frame: Frame, args: list[Term]) -> Node:
    """``(nl_transitive all agent read some book)`` — *every agent read a book*.

    Two quantifiers, and their relative scope is exactly what the lesson asks
    about, so they have to survive into the sentence as separate constituents
    rather than being flattened into a string by the generator.
    """
    q1, subject, relation, q2, obj = (_str(a) for a in args[:5])
    return pred_rel(quant(q1, _as_np(subject, det="bare"), None),
                    lex(V, relation),
                    quant(q2, _as_np(obj, det="bare"), None))


_BUILDERS = {
    "Bare": _build_bare,
    "Labelled": _build_labelled,
    "Enumerated": _build_enumerated,
    "PredAttr": _build_pred_attr,
    "PredIdent": _build_pred_ident,
    "PredIdentRev": _build_pred_ident_rev,
    "ObjKind": _build_obj_kind,
    "ObjFull": _build_obj_full,
    "PredRel": _build_pred_rel,
    "PredRel3": _build_pred_rel3,
    "Reports": _build_reports,
    "Spatial": _build_spatial,
    "Indexed": _build_indexed,
    "IndexedCond": _build_indexed_cond,
    "Mapping": _build_mapping,
    "Coord": _build_coord,
    "Neg": _build_neg,
    "Compare": _build_compare,
    "Quant": _build_quant,
    "NLClaim": _build_nl_claim,
    "NLTransitive": _build_nl_transitive,
}


# ======================================================================
# questions
# ======================================================================
#: query heads that ask for a yes or a no. Recognised by head rather than by
#: inspecting the answer set, because the answer set is not available here and
#: because these are the heads whose *form* is polar regardless of the options.
_POLAR = frozenset({
    "accept", "balanced", "palindrome", "holds", "has", "same_entity",
    "will_succeed", "holds_in_target", "more_than", "none", "predictively_closed",
    "is_valid", "consistent", "entails", "provable", "reachable", "terminates",
})

#: query head -> the wh-word it asks with. Everything not listed asks "what",
#: which is the right default for a head that names a value.
_WH = {
    "which": "which", "which_object": "which", "which_color": "what",
    "who": "who", "most_reliable_in": "who", "works_in_city": "which",
    "how_many": "how_many", "count_readings": "how_many",
    "count_admissible_instantiations": "how_many",
    "where": "where", "room_of": "where", "believes_ball_in": "where",
    "when": "when", "why": "why", "how": "how",
    "max_depth": "how_many", "next": "what", "answer": "what",
}


def compile_query(term: Term) -> Node:
    """Turn a query structure into a question construction.

    Three shapes cover the curriculum: a polar question, a content question, and
    an alternative question. Which one is chosen is a fact about the *query*, so
    it is decided here rather than in each grammar — a grammar decides how to
    *form* a question, never what is being asked.
    """
    from .syntax import alt_question, wh_question, yn_question

    if term.type not in ("pred", "rel", "node"):
        return wh_question("what", compile_term(term))
    head, *rest = term.value
    head = str(head)
    args = [a for a in rest if isinstance(a, Term)]

    if head == "classify" and args:
        # the options are ordinary words and must be translated; leaving them as
        # symbols is how a Chinese question ends up reading "1high或low"
        return alt_question(compile_term(args[0]), [_leaf("high"), _leaf("low")])
    body = _query_body(head, args)
    if head in _POLAR:
        return yn_question(body)
    return wh_question(_WH.get(head, "what"), body)


#: Query heads that need their own analysis, because a head means something
#: different asked than asserted. ``which`` as a predicate would be a relation
#: between a colour and a shape; as a query it *is* the noun phrase being asked
#: about, and compiling it the predicate way produces "which green which disc".
_QUERY_BODY = {
    "which": lambda a: _as_np(a[1].value, det="def", adjectives=[_str(a[0])]),
    "which_object": lambda a: _as_np(a[0].value, det="def"),
    "find": lambda a: _as_np(a[0].value, det="def"),
    "the": lambda a: _as_np(a[-1].value, det="def", adjectives=[_str(a[0])]),
    "accept": lambda a: pred_attr(_string_np(a[0]), adj("accepted")),
    "balanced": lambda a: pred_attr(_the("string"), adj("balanced")),
    "palindrome": lambda a: pred_attr(_the("string"), adj("palindrome")),
    "value_of": lambda a: labelled(_label("value of"), compile_term(a[0])),
    "at": lambda a: labelled(_label("symbol at position"), compile_term(a[0])),
    "refers_to": lambda a: labelled(_label("referent of"), compile_term(a[0])),
}


def _the(lemma: str) -> Node:
    return _as_np(lemma, det="def")


def _string_np(term: Term) -> Node:
    """``the string bbba`` — a labelled symbol, not a bare one.

    Worth the extra node: *is bbba accepted?* reads as though ``bbba`` were a
    name, and in a lesson about formal languages the fact that it is a string is
    the part the learner needs.
    """
    return labelled(_the("string"), compile_term(term))


def _query_body(head: str, args: list[Term]) -> Node:
    """What the question is *about*, before it is made interrogative.

    Unrecognised heads become a labelled row rather than a predication. This is
    deliberate: predicate-frame inference is tuned for assertions, and applying
    it to a query head invents an agent and a patient the question does not
    have. A labelled row is duller and always says the right thing.
    """
    if not args:
        return _label(head)
    special = _QUERY_BODY.get(head)
    if special is not None:
        try:
            return special(args)
        except (IndexError, AttributeError):            # pragma: no cover
            pass
    compiled = [compile_term(a) for a in args]
    words = _label(head)
    return labelled(words, compiled[0]) if len(compiled) == 1 \
        else enumerated(words, compiled)


# ======================================================================
# whole episodes
# ======================================================================
def compile_episode(term: Term) -> tuple[list[Node], Node | None]:
    """Split an episode into its blocks and its question.

    Returns ``(blocks, query)``. The query is separated because forming a
    question is a construction in its own right and every language does it
    differently — the whole reason it is not just another block.
    """
    if term.type != "record":
        return [compile_term(term)], None
    blocks: list[Node] = []
    query: Node | None = None
    for name, value in term.value:
        if name in ("query", "utterance") and query is None:
            query = compile_query(value)
            continue
        items = list(value.children) if value.type == "list" else [value]
        blocks.append(text_block(name, [compile_term(i) for i in items],
                                 is_list=value.type == "list"))
    return blocks, query
