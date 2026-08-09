"""The language layer: English by default, and the seam for adding another."""

from __future__ import annotations

import re

import pytest

import langcurriculum as lc
from langcurriculum.languages import (DEFAULT_LANGUAGE, LANGUAGE_ALIASES, Lexicon,
                                      get_language, language_codes,
                                      languages, register_language)

IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]
IDS = [l.id for l in IMPLEMENTED]


# ---------------------------------------------------------------- defaults
def test_english_is_the_default_everywhere():
    assert DEFAULT_LANGUAGE == "english"
    assert language_codes()[0] == "english"
    assert lc.get("unification").example(0).language == "english"
    assert next(lc.iter_records("unification", n=1))["language"] == "english"
    assert lc.evaluate(lc.constant_agent("x"), "unification", n=2).language == "english"


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_the_default_prompt_is_prose_not_a_notation(lesson):
    """No caller should have to pass a flag to get English."""
    obs = lesson.example(3).observation
    assert not obs.lstrip().startswith("{"), f"{lesson.id} still renders as a record"
    assert re.match(r"^[A-Z]", obs.strip()), "a sentence starts with a capital"
    assert obs.rstrip()[-1] in ".?:", "a sentence ends with punctuation"


@pytest.mark.parametrize("lesson", IMPLEMENTED, ids=IDS)
def test_english_carries_enough_to_decide_the_answer(lesson):
    """If two episodes read the same in English but disagree, prose lost something."""
    seen: dict[str, str] = {}
    for ex in lesson.examples(60, language="english"):
        prior = seen.get(ex.prompt)
        assert prior is None or prior == ex.answer, \
            f"{lesson.id}: two answers behind one English prompt (seed {ex.seed})"
        seen[ex.prompt] = ex.answer


# The stronger, multilingual form of this check — that no template drops an
# argument in any language — lives in tests/test_grammar.py.


# ---------------------------------------------------------------- registry
def test_the_shipped_packs_declare_what_they_are():
    # The eagerly-registered core. Grammar-backed languages are built on demand
    # from the language database and cached into the same registry, so an exact
    # set assertion would depend on what a prior test happened to ask for.
    codes = set(language_codes())
    assert {"english", "english_synonym", "spanish", "chinese", "symbols",
            "turkish", "swahili"} <= codes
    kinds = {l["code"]: l["kind"] for l in languages()}
    assert kinds["english"] == kinds["spanish"] == kinds["chinese"] == "natural"
    assert kinds["turkish"] == kinds["swahili"] == "natural"
    assert kinds["symbols"] == "formal"
    assert all(l["description"] for l in languages())


@pytest.mark.parametrize("code", ["english", "spanish", "chinese"])
def test_every_natural_pack_ships_a_substantial_vocabulary(code):
    lang = get_language(code)
    counts = lang.lexicon.vocabulary.counts()
    assert counts["total"] >= 300, counts
    assert counts["nouns"] >= 80 and counts["adjectives"] >= 20
    assert lang.grammar_notes, "a pack must say what grammar it implements"


@pytest.mark.parametrize("code", ["spanish", "chinese"])
def test_a_non_english_pack_translates_rather_than_substituting(code):
    """If the output were English with swapped words it would still be English."""
    lang = get_language(code)
    obs = lc.get("symbol_grounding").example(0, language=code).observation
    assert "In the scene" not in obs and " is a " not in obs
    assert lang.lexicon.field_intros, "the pack must frame its own sections"
    # It is the *grammar* that makes this more than word substitution: the
    # parameters that decide order, agreement and question formation have to
    # differ from English, not just the vocabulary.
    g = lang.grammar
    english = get_language("english").grammar
    differs = [k for k in ("adj", "wh_fronting", "copula_overt", "conditional",
                           "numeral_forces_plural", "det")
               if getattr(g.order, k) != getattr(english.order, k)]
    assert differs or g.concord.adjective, \
        f"{code} has the same parameters as English in every dimension"
    assert len(lang.lexicon.predicate_words) > 100, \
        "the relational lexicon must be the pack's own"


def test_the_notation_is_reachable_under_its_aliases():
    assert LANGUAGE_ALIASES["invented"] == "symbols"
    assert get_language("invented").code == "symbols"
    ex = lc.get("lexicon_induction").example(0, language="invented")
    assert ex.language == "symbols", "a record names the pack, not the alias"
    assert lc.evaluate(lc.constant_agent("o0"), "unification",
                       n=2, language="invented").language == "symbols"
    assert ex.observation.startswith("{"), "the notation should still be s-expressions"


def test_an_unknown_language_names_the_ones_there_are():
    with pytest.raises(ValueError, match="english"):
        get_language("volapuk")


def test_a_language_object_passes_through():
    en = get_language("english")
    assert get_language(en) is en
    assert lc.get("unification").example(0, language=en).language == "english"


# ---------------------------------------------------------------- variants
def test_the_synonym_variant_holds_words_out_of_the_question_only():
    """The body keeps the trained word; the question uses one never seen."""
    lesson = lc.get("symbol_grounding")
    plain = lesson.example(0, language="english")
    held = lesson.example(0, language="english_synonym")
    assert plain.answer == held.answer
    body_p, q_p = plain.observation.rsplit("\n", 1)
    body_h, q_h = held.observation.rsplit("\n", 1)
    assert body_p == body_h, "only the question is substituted"
    assert q_p != q_h, "the question should use the held-out word"
    assert any(s in q_h for s in ("crimson", "azure", "emerald", "golden", "violet",
                                  "amber", "block", "ball", "funnel", "wedge",
                                  "plate", "stick"))


def test_the_notation_stays_available_and_is_shorter():
    lesson = lc.get("quantification")
    prose = lesson.example(1, language="english")
    notation = lesson.example(1, language="symbols")
    assert prose.answer == notation.answer
    assert len(notation.observation) < len(prose.observation)


# ---------------------------------------------------------------- the seam
def test_a_new_language_needs_only_parameters_and_words():
    """The seam, exercised: declare a grammar, register it, everything picks it up.

    Deliberately a *typologically* odd toy — verb-final, postpositional, no
    articles, adjective after the noun — because a test that registers another
    SVO language proves only that the registry works, not that the engine is
    parameterized.
    """
    from langcurriculum.grammar.adapter import GrammarLanguage
    from langcurriculum.grammar.linearize import Grammar, Typography, WordOrder

    class Toy(Grammar):
        code = "_toy"
        name = "Toy (test)"
        order = WordOrder(clause="SOV", adj="NA", det="ND", adposition="post",
                          wh_fronting=False, copula_overt=False)
        typography = Typography(full_stop=" .")
        notes = ("verb-final, postpositional, no articles",
                 "NOT attempted: anything at all — it is a test fixture")

        def __init__(self):
            super().__init__()
            self.closed = {"and": "ond", "not": "nay", "the": "", "a": ""}
            self.field_intros = {"scene": "Inway ethay ecenesay:"}

    register_language(GrammarLanguage(Toy()))
    try:
        ex = lc.get("symbol_grounding").example(0, language="_toy")
        assert ex.language == "_toy"
        assert "Inway ethay ecenesay:" in ex.observation
        assert ex.answer == lc.get("symbol_grounding").example(0).answer, \
            "a language changes the words, never the answer"
        report = lc.evaluate(lc.constant_agent("o0"), "symbol_grounding",
                             n=3, language="_toy")
        assert report.language == "_toy"
        rec = next(lc.iter_records("symbol_grounding", n=1, language="_toy"))
        assert rec["language"] == "_toy"
    finally:
        lc.LANGUAGES.pop("_toy", None)

def test_the_lexicon_supplies_the_agreement_material_the_syntax_lessons_use():
    """Those lessons are about morphology, so their words come from the pack."""
    from langcurriculum._support import extra

    lex = get_language("english").lexicon
    assert extra.verbs() == list(lex.verbs)
    assert extra.noun_forms() == [tuple(x) for x in lex.noun_forms]
    assert extra.agree_forms() == [tuple(x) for x in lex.agreement_forms]
    assert extra.pronoun() == dict(lex.pronouns)
    assert extra.gender() == dict(lex.name_gender)
    assert lex.verbs and lex.noun_forms and lex.pronouns


def test_the_agreement_material_follows_the_language_it_is_asked_for():
    """It was read once at import, so it never followed anything.

    These lessons are *about* morphology and their sentences are built from
    inflected words rather than translated at render time. Bound to the
    default language at import, an agreement lesson asked for in Spanish came
    out entirely in English with only its heading translated.
    """
    from langcurriculum._support import extra

    token = extra.ACTIVE_LANGUAGE.set("spanish")
    try:
        assert extra.supplies("noun_forms"), "Spanish should supply its own"
        assert extra.verbs() == list(get_language("spanish").lexicon.verbs)
        assert extra.pronoun()["m"] == "él"
    finally:
        extra.ACTIVE_LANGUAGE.reset(token)
    assert extra.pronoun()["m"] == "he"


def test_a_pack_that_supplies_nothing_falls_back_whole():
    """Half a table would put half a sentence in the wrong language."""
    from langcurriculum._support import extra

    token = extra.ACTIVE_LANGUAGE.set("rus")
    try:
        assert not extra.supplies("noun_forms")
        assert extra.noun_forms() == extra.gender.__globals__["_ENGLISH"].noun_forms
        # and its article too, since English nouns want an English article
        assert extra.determiner() == "the"
    finally:
        extra.ACTIVE_LANGUAGE.reset(token)


@pytest.mark.parametrize("field,count", sorted(
    __import__("langcurriculum._support.extra", fromlist=["x"]).PARALLEL_FIELDS.items()))
def test_a_parallel_table_has_the_same_length_in_every_pack(field, count):
    """Not a style rule — the cross-language invariant depends on it.

    ``rng.choice`` consumes a variable number of bits depending on how long the
    sequence is, so a pack offering five nouns where English offers six shifts
    the whole random stream and moves the correct option. Equal lengths keep
    the stream identical and change only the words.
    """
    for code in ("english", "spanish"):
        supplied = getattr(get_language(code).lexicon, field, None) or ()
        if supplied:
            assert len(supplied) == count, f"{code}.{field} has {len(supplied)}"


def test_the_lexicon_exposes_the_closed_class_a_new_pack_must_supply():
    lex = get_language("english").lexicon
    for attr in ("definite", "indefinite", "copula_sg", "copula_pl", "negation",
                 "conjunction", "disjunction", "yes", "no", "question_mark"):
        assert getattr(lex, attr), attr
    assert lex.quantifiers and lex.field_intros and lex.predicate_words
    g = get_language("english").grammar
    assert g.join_list(["a", "b", "c"]) == "a, b and c"
    assert g.word("left_of") == "to the left of"


def test_invented_vocabulary_survives_translation_into_english():
    """Per-episode coinages are a lesson property, not a notation artefact."""
    ex = lc.get("lexicon_induction").example(0, language="english")
    hidden = ex.metadata["hidden"]["lexicon"]
    for coined in hidden:
        assert coined in ex.observation, "the invented words must reach the prose"
