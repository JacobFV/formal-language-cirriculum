"""The language layer: English by default, and the seam for adding another."""

from __future__ import annotations

import re

import pytest

import langcurriculum as lc
from langcurriculum.languages import (DEFAULT_LANGUAGE, LANGUAGE_ALIASES, Lexicon,
                                      NaturalLanguage, get_language, language_codes,
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
    codes = set(language_codes())
    assert codes == {"english", "english_synonym", "spanish", "chinese", "symbols"}
    kinds = {l["code"]: l["kind"] for l in languages()}
    assert kinds["english"] == kinds["spanish"] == kinds["chinese"] == "natural"
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
    assert len(lang.lexicon.query_templates) > 100


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
def test_a_new_language_needs_only_words():
    """The point of the pack: register one, and everything picks it up."""
    pig = Lexicon(
        copula_sg="isay", copula_pl="areay", conjunction="anday",
        field_intros={"scene": "Inway ethay ecenesay:"},
        query_templates={"which": "ichwhay objectway isay ethay {0} {1}?"},
        predicate_templates={"obj/5": "{0} isay away {1} {2} atway ({3}, {4})"},
    )
    register_language(NaturalLanguage(code="_pig", name="Pig Latin (test)",
                                      lexicon=pig, description="a test pack"))
    try:
        ex = lc.get("symbol_grounding").example(0, language="_pig")
        assert ex.language == "_pig"
        assert "Inway ethay ecenesay:" in ex.observation
        assert "isay away" in ex.observation
        assert ex.answer == lc.get("symbol_grounding").example(0).answer, \
            "a language changes the words, never the answer"
        report = lc.evaluate(lc.constant_agent("o0"), "symbol_grounding",
                             n=3, language="_pig")
        assert report.language == "_pig"
        rec = next(lc.iter_records("symbol_grounding", n=1, language="_pig"))
        assert rec["language"] == "_pig"
    finally:
        lc.LANGUAGES.pop("_pig", None)


def test_the_lexicon_supplies_the_agreement_material_the_syntax_lessons_use():
    """Those lessons are about morphology, so their words come from the pack."""
    from langcurriculum._support import extra

    lex = get_language("english").lexicon
    assert extra.VERBS == list(lex.verbs)
    assert extra.NOUN_FORMS == [tuple(x) for x in lex.noun_forms]
    assert extra.AGREE_FORMS == [tuple(x) for x in lex.agreement_forms]
    assert extra.PRONOUN == dict(lex.pronouns)
    assert extra.GENDER == dict(lex.name_gender)
    assert lex.verbs and lex.noun_forms and lex.pronouns


def test_the_lexicon_exposes_the_closed_class_a_new_pack_must_supply():
    lex = get_language("english").lexicon
    for attr in ("definite", "indefinite", "copula_sg", "copula_pl", "negation",
                 "conjunction", "disjunction", "yes", "no", "question_mark"):
        assert getattr(lex, attr), attr
    assert lex.operators and lex.prepositions and lex.quantifiers
    assert lex.field_intros and lex.predicate_templates and lex.query_templates
    assert get_language("english").join_list(["a", "b", "c"]) == "a, b and c"
    assert lex.word_for("left_of") == "to the left of"


def test_invented_vocabulary_survives_translation_into_english():
    """Per-episode coinages are a lesson property, not a notation artefact."""
    ex = lc.get("lexicon_induction").example(0, language="english")
    hidden = ex.metadata["hidden"]["lexicon"]
    for coined in hidden:
        assert coined in ex.observation, "the invented words must reach the prose"
