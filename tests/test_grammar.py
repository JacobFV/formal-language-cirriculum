"""Grammar invariants per language, asserted rather than eyeballed.

These are the properties a native reader would notice immediately, written as
checks: article and adjective agreement in Spanish, measure words and the
absence of spacing in Chinese, and — for every natural language — that the
question was formed the way that language forms questions and that nothing was
lost on the way from the structure to the sentence.
"""

from __future__ import annotations

import random
import re

import pytest

import langcurriculum as lc
from langcurriculum._structure import leaves
from langcurriculum.languages import get_language

NATURAL = [c for c in lc.language_codes() if get_language(c).kind == "natural"]
IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]
IDS = [l.id for l in IMPLEMENTED]

CJK = r"㐀-䶿一-鿿　-〿＀-￯"
#: a formal call — ``t(a, b, c)``, ``op(x, 减, 5)`` — keeps half-width punctuation
#: even inside Chinese text, so the typography checks skip over one
CALL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\([^()]*\)")


# ======================================================================
# every natural language
# ======================================================================
@pytest.mark.parametrize("code", NATURAL)
def test_the_pack_declares_the_grammar_it_implements(code):
    lang = get_language(code)
    assert lang.grammar_notes, f"{code} must say what it does"
    assert lang.lexicon.vocabulary.counts()["total"] >= 300


@pytest.mark.parametrize("code", NATURAL)
def test_no_two_prompts_in_a_language_carry_different_answers(code):
    """The property that says the prose still determines the answer."""
    for lesson in IMPLEMENTED[::4]:
        seen: dict[str, str] = {}
        for ex in lesson.examples(30, language=code):
            prior = seen.get(ex.prompt)
            assert prior is None or prior == ex.answer, \
                f"{code}/{lesson.id}: two answers behind one prompt (seed {ex.seed})"
            seen[ex.prompt] = ex.answer


@pytest.mark.parametrize("code", NATURAL)
def test_the_question_keeps_every_argument_it_was_given(code):
    """No template may quietly ask about less than the query carries.

    This is the check that caught a dropped anchor in English and, when the
    other packs were first written, 18 dropped arguments in Spanish and 33 in
    Chinese. A template with fewer slots than the query has arguments is now
    rejected in favour of the generic question, so this stays at zero.
    """
    lang = get_language(code)
    lex = lang.lexicon
    for lesson in IMPLEMENTED:
        for seed in (0, 4, 11):
            obs, _, _, _ = type(lesson).generate(random.Random(seed))
            if obs.type != "record":
                continue
            query = obs.field("query")
            if query is None:
                continue
            question = lang.render(obs).splitlines()[-1].casefold()
            for leaf in (x for c in query.children for x in leaves(c)):
                if leaf.type not in ("ident", "token", "str", "num"):
                    continue
                raw = str(leaf.value)
                forms = lex.vocabulary.forms(raw) | {
                    lang.text(leaf.value), lex.quantifiers.get(raw, ""),
                    lex.operators.get(raw, ""), lex.prepositions.get(raw, ""),
                    lex.synonyms.get(raw, ""), raw.replace("_", " ")}
                assert any(f and f.casefold() in question for f in forms), \
                    f"{code}/{lesson.id}: the question dropped {raw!r} (seed {seed})"


@pytest.mark.parametrize("code", NATURAL)
def test_the_answer_set_stays_distinguishable(code):
    """Translating the options must never merge two of them."""
    for lesson in IMPLEMENTED:
        ex = lesson.example(3, language=code)
        assert len(set(ex.choices)) == len(ex.choices), f"{code}/{lesson.id}"
        assert ex.answer in ex.choices


@pytest.mark.parametrize("code", NATURAL)
def test_translation_never_merges_two_identifiers_in_one_episode(code):
    """A coined name may collide with a real word; it must not collide with another name.

    Generators coin identifiers freely, and now and then one lands on a word the
    pack knows — a causal variable called ``big`` renders as ``grande``. That is
    cosmetic: the renaming is consistent, so the episode reads the same way and
    is answerable. What would *not* be cosmetic is two distinct identifiers
    rendering as one string, which would make the episode ambiguous. This
    asserts that never happens.
    """
    from langcurriculum._structure import walk

    lang = get_language(code)
    for lesson in IMPLEMENTED:
        for seed in range(4):
            obs, _, _, _ = type(lesson).generate(random.Random(seed))
            seen: dict[str, str] = {}
            for term in walk(obs):
                if term.type not in ("ident", "token") or term.children:
                    continue
                if not isinstance(term.value, str):
                    continue
                rendered = lang.text(term.value)
                assert seen.get(rendered, term.value) == term.value, (
                    f"{code}/{lesson.id} seed {seed}: {seen.get(rendered)!r} and "
                    f"{term.value!r} both render as {rendered!r}")
                seen[rendered] = term.value


# ======================================================================
# Spanish
# ======================================================================
ES = get_language("spanish")


def test_spanish_agrees_the_article_and_adjective_with_the_noun():
    assert ES.noun_phrase("cube", adjectives=["red"], determiner="indef") == "un cubo rojo"
    assert ES.noun_phrase("sphere", adjectives=["red"], determiner="indef") == "una esfera roja"
    assert ES.noun_phrase("cube", adjectives=["red"], determiner="def") == "el cubo rojo"
    assert ES.noun_phrase("sphere", adjectives=["red"], determiner="def") == "la esfera roja"


def test_spanish_agrees_in_number_too():
    assert ES.noun_phrase("cube", adjectives=["red"], determiner="def",
                          plural=True) == "los cubos rojos"
    assert ES.noun_phrase("sphere", adjectives=["red"], determiner="def",
                          plural=True) == "las esferas rojas"


def test_spanish_puts_the_adjective_after_the_noun():
    phrase = ES.noun_phrase("cube", adjectives=["yellow"], determiner="indef")
    assert phrase.index("cubo") < phrase.index("amarillo")


def test_every_spanish_noun_carries_a_gender_and_a_plural():
    for key, noun in ES.lexicon.vocabulary.nouns.items():
        assert noun.gender in ("m", "f"), key
        assert noun.plural, key


def test_every_spanish_adjective_carries_four_agreement_forms():
    for key, adj in ES.lexicon.vocabulary.adjectives.items():
        assert adj.ms and adj.fs and adj.mp and adj.fp, key


def test_every_spanish_noun_agrees_with_every_spanish_adjective():
    """Agreement over the whole vocabulary, not a spot check.

    137 nouns x 27 adjectives: the article has to match the noun's gender and
    the adjective has to end in the form that agrees with it, in the singular
    and in the plural.
    """
    vocab = ES.lexicon.vocabulary
    for nkey, noun in vocab.nouns.items():
        for akey, adj in vocab.adjectives.items():
            for plural in (False, True):
                phrase = ES.noun_phrase(nkey, adjectives=[akey],
                                        determiner="indef", plural=plural)
                assert phrase.endswith(adj.agree(noun.gender, plural=plural)), \
                    f"{nkey}+{akey} plural={plural}: {phrase}"
                head = noun.plural if plural else noun.lemma
                assert head in phrase, f"{nkey}: {phrase}"
                if not plural:
                    article = "un" if noun.gender == "m" else "una"
                    if noun.lemma.lower() in {"agua", "área", "arma", "aula", "alma",
                                              "hambre", "águila", "ala", "acta",
                                              "hacha", "ancla", "aria", "asa", "hada"}:
                        article = "un"
                    assert phrase.startswith(article + " "), f"{nkey}+{akey}: {phrase}"


def test_spanish_scene_sentences_agree_in_the_wild():
    """The agreement has to survive the templates, not just the helper."""
    text = " ".join(lc.get("symbol_grounding").example(s, language="spanish").observation
                    for s in range(60))
    for bad in ("un esfera", "una cubo", "esfera rojo", "cubo roja",
                "una prisma", "un varilla"):
        assert bad not in text, bad
    assert "es un cubo" in text and "es un" in text


def test_spanish_opens_and_closes_its_questions():
    for lesson in IMPLEMENTED[::3]:
        q = lesson.example(2, language="spanish").observation.splitlines()[-1]
        if q.endswith("?"):
            # the opening mark scopes the interrogative clause, which is not
            # always the whole sentence: "Todos son rojos, ¿verdadero o falso?"
            assert "¿" in q, f"{lesson.id}: {q}"


def test_spanish_uses_e_before_i_and_u_before_o():
    assert ES.join_list(["pájaro", "insecto"]) == "pájaro e insecto"
    assert ES.join_list(["rojo", "azul"]) == "rojo y azul"
    assert ES.disjoin(["siete", "ocho"]) == "siete u ocho"
    assert ES.disjoin(["siete", "nueve"]) == "siete o nueve"


def test_spanish_takes_el_before_a_stressed_initial_a():
    """``el agua fría``: masculine article, feminine adjective."""
    assert ES.noun_phrase("water", determiner="def") == "el agua"
    assert ES.noun_phrase("water", adjectives=["red"], determiner="def") == "el agua roja"
    assert ES.noun_phrase("water", determiner="def", plural=True).startswith("las ")
    # and not for an unstressed initial a-
    assert ES.noun_phrase("clay", determiner="def") == "la arcilla"


def test_spanish_uses_estar_for_location():
    text = lc.get("symbol_grounding").example(0, language="spanish").observation
    assert "está en" in text and "es en" not in text


def test_spanish_prose_is_not_english_with_swapped_words():
    text = lc.get("symbol_grounding").example(0, language="spanish").observation
    assert " is " not in text and "In the scene" not in text
    assert text.startswith("En la escena")


# ======================================================================
# Chinese
# ======================================================================
ZH = get_language("chinese")


def test_chinese_uses_a_measure_word_to_count_and_to_point():
    assert ZH.noun_phrase("cube", determiner="indef") == "一个立方体"
    assert ZH.noun_phrase("cube", determiner="def") == "这个立方体"
    assert ZH.noun_phrase("book", count=3) == "3本书"
    assert ZH.classifier("book") == "本"
    assert ZH.classifier("rod") != ""


def test_every_chinese_noun_carries_a_classifier():
    for key, noun in ZH.lexicon.vocabulary.nouns.items():
        assert noun.classifier, key


def test_chinese_links_modifiers_with_de_where_the_adjective_needs_it():
    assert ZH.adjective("red") == "红色的"
    assert ZH.noun_phrase("cube", adjectives=["red"], determiner="indef") == "一个红色的立方体"
    monosyllabic = [k for k, a in ZH.lexicon.vocabulary.adjectives.items() if not a.linker]
    assert monosyllabic, "some adjectives must attach without 的"
    for key in monosyllabic:
        assert not ZH.adjective(key).endswith("的"), key


def test_chinese_does_not_inflect():
    assert ZH.pluralize("立方体") == "立方体"
    assert ZH.noun_phrase("cube", plural=True) == ZH.noun_phrase("cube")


def test_chinese_writes_without_spaces_between_characters():
    """Bullet indentation aside, nothing separates Chinese characters."""
    space_by_cjk = re.compile(rf"[{CJK}] | [{CJK}]")
    bullet = re.compile(r"^\s*-\s*")
    for lesson in IMPLEMENTED[::3]:
        for line in lesson.example(1, language="chinese").observation.splitlines():
            line = CALL.sub("", bullet.sub("", line))
            assert not space_by_cjk.search(line), f"{lesson.id}: {line[:120]!r}"


def test_chinese_uses_full_width_punctuation():
    halfwidth = re.compile(rf"[{CJK}][,;:?!]|[,;:?!][{CJK}]")
    for lesson in IMPLEMENTED[::3]:
        text = CALL.sub("", lesson.example(1, language="chinese").observation)
        assert not halfwidth.search(text), f"{lesson.id}: {text[:120]!r}"


def test_chinese_forms_questions_with_particles_not_inversion():
    """A question ends in ？ and asks with 吗 or an in-situ wh-word."""
    markers = ("吗", "什么", "哪", "谁", "多少", "几", "是否", "还是", "呢")
    checked = 0
    for lesson in IMPLEMENTED:
        q = lesson.example(2, language="chinese").observation.splitlines()[-1]
        if not q.endswith("？"):
            continue
        checked += 1
        assert any(m in q for m in markers), f"{lesson.id}: {q}"
    assert checked > 100, "most lessons should end in a question"


def test_chinese_yes_no_questions_use_a_particle():
    q = lc.get("finite_state_language").example(0, language="chinese").observation.splitlines()[-1]
    assert q.endswith("吗？") or "是否" in q or "还是" in q


def test_chinese_coordinates_clauses_with_the_full_width_semicolon():
    assert ZH.join_list(["甲", "乙", "丙"]) == "甲、乙和丙"
    assert ZH.join_clauses(["甲是人", "乙是人"]) == "甲是人；乙是人"


def test_chinese_prose_is_not_english_with_swapped_words():
    text = lc.get("symbol_grounding").example(0, language="chinese").observation
    assert " is " not in text and "In the scene" not in text
    assert text.startswith("场景中：")


def test_chinese_never_capitalizes():
    assert ZH.lexicon.capitalizes is False
    assert ZH.sentence("场景中：甲") == "场景中：甲。"
