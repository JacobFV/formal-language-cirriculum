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
from langcurriculum.grammar.features import EMPTY as EMPTY_FS, FS
from langcurriculum.languages import get_language

NATURAL = [c for c in lc.language_codes() if get_language(c).kind == "natural"]
IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]
IDS = [l.id for l in IMPLEMENTED]

CJK = r"㐀-䶿一-鿿　-〿＀-￯"
#: a formal call — ``t(a, b, c)``, ``op(x, 减, 5)`` — keeps half-width punctuation
#: even inside Chinese text, so the typography checks skip over one
CALL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\([^()]*\)")
FS_PL = FS({"num": "pl"})


# ======================================================================
# every natural language
# ======================================================================
@pytest.mark.parametrize("code", NATURAL)
def test_the_pack_declares_the_grammar_it_implements(code):
    lang = get_language(code)
    assert lang.grammar_notes, f"{code} must say what it does"
    if getattr(lang, "partial_vocabulary", False):
        # A pack may ship before its vocabulary covers the whole curriculum —
        # a grammar is useful with a partial lexicon and a lexicon is useless
        # without a grammar. What it may not do is be quiet about it: the
        # coverage is asserted against a declared floor and reported by the CLI,
        # so a reader knows an untranslated word is a gap and not a bug.
        assert lang.lexicon.vocabulary.counts()["total"] >= 60, \
            f"{code} ships too little vocabulary to be worth presenting"
        assert any("NOT attempted" in n for n in lang.grammar_notes), \
            f"{code} must say what it does not attempt"
    else:
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
# Spanish — asserted against the grammar, which is where the behaviour lives
# ======================================================================
from langcurriculum.grammar.grammars import get_grammar          # noqa: E402
from langcurriculum.grammar.grammars.spanish import EL_AGUA      # noqa: E402
from langcurriculum.grammar.syntax import (                      # noqa: E402
    adj, mk_cn, mk_np, noun, pred_loc, sym,
)

ES = get_grammar("spanish")
ZH = get_grammar("chinese")


def np(key, *adjectives, plural=False, **kw):
    node = mk_np(mk_cn(noun(key), *[adj(a) for a in adjectives]), **kw)
    return node.but(num="pl") if plural else node


def test_spanish_agrees_the_article_and_adjective_with_the_noun():
    assert ES.lin(np("cube", "red", det="indef")) == "un cubo rojo"
    assert ES.lin(np("sphere", "red", det="indef")) == "una esfera roja"
    assert ES.lin(np("cube", "red", det="def")) == "el cubo rojo"
    assert ES.lin(np("sphere", "red", det="def")) == "la esfera roja"


def test_spanish_agrees_in_number_too():
    assert ES.lin(np("cube", "red", det="def", plural=True)) == "los cubos rojos"
    assert ES.lin(np("sphere", "red", det="def", plural=True)) == "las esferas rojas"


def test_spanish_puts_the_adjective_after_the_noun():
    phrase = ES.lin(np("cube", "yellow", det="indef"))
    assert phrase.index("cubo") < phrase.index("amarillo")


def test_every_spanish_noun_carries_a_gender_and_a_plural():
    for key, n in ES.vocabulary.nouns.items():
        assert n.gender in ("m", "f"), key
        assert n.plural, key


def test_every_spanish_adjective_carries_four_agreement_forms():
    for key, a in ES.vocabulary.adjectives.items():
        assert a.ms and a.fs and a.mp and a.fp, key


def test_every_spanish_noun_agrees_with_every_spanish_adjective():
    """Agreement over the whole vocabulary, not a spot check.

    137 nouns x 27 adjectives x singular/plural. Under the old pack this
    exercised a hand-written ``noun_phrase``; it now exercises one
    ``Concord`` declaration and the shared unification walk, which is the
    change the rewrite was for.
    """
    vocab = ES.vocabulary
    for nkey, n in vocab.nouns.items():
        for akey, a in vocab.adjectives.items():
            for plural in (False, True):
                phrase = ES.lin(np(nkey, akey, det="indef", plural=plural))
                assert phrase.endswith(a.agree(n.gender, plural=plural)), \
                    f"{nkey}+{akey} plural={plural}: {phrase}"
                head_form = n.plural if plural else n.lemma
                assert head_form in phrase, f"{nkey}: {phrase}"
                if not plural:
                    article = "un" if n.gender == "m" else "una"
                    if n.lemma.lower() in EL_AGUA:
                        article = "un"
                    assert phrase.startswith(article + " "), f"{nkey}+{akey}: {phrase}"


def test_spanish_scene_sentences_agree_in_the_wild():
    """The agreement has to survive the whole walk, not just the phrase builder."""
    text = " ".join(lc.get("symbol_grounding").example(s, language="spanish").observation
                    for s in range(60))
    for bad in ("un esfera", "una cubo", "esfera rojo", "cubo roja",
                "una prisma", "un varilla"):
        assert bad not in text, bad
    assert "es un cubo" in text


def test_spanish_opens_and_closes_its_questions():
    for lesson in IMPLEMENTED[::3]:
        q = lesson.example(2, language="spanish").observation.splitlines()[-1]
        if q.endswith("?"):
            assert "¿" in q, f"{lesson.id}: {q}"


def test_spanish_uses_e_before_i_and_u_before_o():
    assert ES.join_list(["pájaro", "insecto"]) == "pájaro e insecto"
    assert ES.join_list(["rojo", "azul"]) == "rojo y azul"
    assert ES.disjoin(["siete", "ocho"]) == "siete u ocho"
    assert ES.disjoin(["siete", "nueve"]) == "siete o nueve"


def test_spanish_takes_el_before_a_stressed_initial_a():
    """``el agua fría``: masculine article, feminine adjective.

    The one place Spanish makes the article and the adjective disagree, and so
    the one place a concord system that propagates a single feature to both is
    wrong by construction.
    """
    assert ES.lin(np("water", det="def")) == "el agua"
    assert ES.lin(np("water", "red", det="def")) == "el agua roja"
    assert ES.lin(np("water", det="def", plural=True)).startswith("las ")
    assert ES.lin(np("clay", det="def")) == "la arcilla"


def test_spanish_uses_estar_for_location():
    """Location takes estar; identity takes ser."""
    assert ES.copula("loc", EMPTY_FS) == "está"
    assert ES.copula("ident", EMPTY_FS) == "es"
    assert ES.sentence(ES.lin(pred_loc(sym("o0"), sym("(4, 8)")))) == "O0 está en (4, 8)."


def test_spanish_prose_is_not_english_with_swapped_words():
    text = lc.get("symbol_grounding").example(0, language="spanish").observation
    assert " is " not in text and "In the scene" not in text
    assert text.startswith("En la escena")


# ======================================================================
# Chinese
# ======================================================================
def test_chinese_uses_a_measure_word_to_count_and_to_point():
    assert ZH.lin(np("cube", det="indef")) == "一个立方体"
    assert ZH.lin(np("cube", det="def")) == "这个立方体"
    assert ZH.lin(mk_np(mk_cn(noun("book")), count=3)) == "3本书"
    assert ZH.classifier("book") == "本"
    assert ZH.classifier("rod") != ""


def test_every_chinese_noun_carries_a_classifier():
    for key, n in ZH.vocabulary.nouns.items():
        assert n.classifier, key


def test_chinese_links_modifiers_with_de_where_the_adjective_needs_it():
    assert ZH.inflect("A", "red", EMPTY_FS) == "红色的"
    assert ZH.lin(np("cube", "red", det="indef")) == "一个红色的立方体"
    monosyllabic = [k for k, a in ZH.vocabulary.adjectives.items() if not a.linker]
    assert monosyllabic, "some adjectives must attach without 的"
    for key in monosyllabic:
        assert not ZH.inflect("A", key, EMPTY_FS).endswith("的"), key


def test_chinese_does_not_inflect():
    assert ZH.inflect("N", "立方体", FS_PL) == "立方体"
    assert ZH.lin(np("cube", plural=True)) == ZH.lin(np("cube"))


def test_chinese_writes_without_spaces_between_characters():
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
    markers = ("吗", "什么", "哪", "谁", "多少", "几", "是否", "还是", "呢")
    checked = 0
    for lesson in IMPLEMENTED:
        q = lesson.example(2, language="chinese").observation.splitlines()[-1]
        if not q.endswith("？"):
            continue
        checked += 1
        assert any(m in q for m in markers), f"{lesson.id}: {q}"
    assert checked > 100, "most lessons should end in a question"


def test_chinese_coordinates_clauses_with_the_full_width_semicolon():
    assert ZH.join_list(["甲", "乙", "丙"]) == "甲、乙和丙"
    assert ZH.join_clauses(["甲是人", "乙是人"]) == "甲是人；乙是人"


def test_chinese_prose_is_not_english_with_swapped_words():
    text = lc.get("symbol_grounding").example(0, language="chinese").observation
    assert " is " not in text and "In the scene" not in text
    assert text.startswith("场景中：")


def test_chinese_never_capitalizes():
    assert ZH.typography.capitalizes is False
    assert ZH.sentence("场景中：甲") == "场景中：甲。"
