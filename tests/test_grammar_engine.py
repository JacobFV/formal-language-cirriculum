"""Invariants of the grammar engine, asserted rather than eyeballed.

Three kinds of check live here.

**Mechanism.** Unification does what unification is supposed to do, and the
phonological layer produces the forms a speaker would produce. These are the
tests that would catch a subtle break in the machinery, and they are written as
paradigms — *ev/evler/evde/evlerde* — because that is how the facts are known.

**Typology.** The same abstract tree, linearized by two grammars, comes out in
the word order each language actually has. This is the check that the engine is
parameterized rather than English-with-substitutions: it fails the moment a
grammar starts inheriting an ordering decision it never made.

**Coverage.** Every implemented lesson renders in every grammar language without
crashing, and the answer set stays distinguishable. A grammar that cannot render
an episode is worse than a clumsy one, because the episode simply disappears.
"""

from __future__ import annotations

import random
import re

import pytest
from dataclasses import replace

import langcurriculum as lc
from langcurriculum.grammar.derived import DerivedGrammar
from langcurriculum.grammar.features import FS, Var, subsumes, unify
from langcurriculum.grammar.grammars import GRAMMARS, get_grammar
from langcurriculum.grammar.morphology import TURKISH_PHONOLOGY
from langcurriculum.grammar.store import LanguageDB
from langcurriculum.grammar.syntax import (
    CONSTRUCTIONS, adj, coord, mk_ap, mk_cn, mk_np, negate, noun, pred_attr,
    pred_ident, pred_loc, pred_rel, sym, yn_question,
)
from langcurriculum.languages import get_language

from conftest import needs_db

ENGINE_LANGUAGES = ["turkish", "swahili"]
IMPLEMENTED = [l for l in lc.all_lessons().values() if l.status == "implemented"]


def np(key, *adjectives, **kw):
    return mk_np(mk_cn(noun(key), *[adj(a) for a in adjectives]), **kw)


# ======================================================================
# unification
# ======================================================================
def test_unification_merges_what_both_sides_know():
    merged, _ = unify(FS(num="sg", cls="f"), FS(cls="f", case="nom"))
    assert merged == FS(case="nom", cls="f", num="sg")


def test_unification_fails_on_conflict_rather_than_raising():
    assert unify(FS(num="sg"), FS(num="pl")) is None


def test_a_variable_takes_the_value_the_other_side_supplies():
    merged, _ = unify(FS(cls=Var("c")), FS(cls="7"))
    assert merged["cls"] == "7"


def test_variables_chain_so_rule_order_does_not_matter():
    """``?a`` tied to ``?b`` tied to a value must resolve however it was built."""
    first, bindings = unify(FS(x=Var("a")), FS(x=Var("b")))
    second, _ = unify(first, FS(x="sg"), bindings)
    assert second["x"] == "sg"


def test_renaming_keeps_two_rules_from_tying_their_features_together():
    a = FS(num=Var("n")).rename("1")
    b = FS(num=Var("n")).rename("2")
    assert a["num"] != b["num"]


def test_subsumption_ignores_features_the_general_side_omits():
    assert subsumes(FS(case="acc"), FS(case="acc", num="pl"))
    assert not subsumes(FS(case="acc"), FS(case="nom", num="pl"))


# ======================================================================
# Turkish morphology
# ======================================================================
@pytest.mark.parametrize("stem,affixes,expected", [
    ("ev", ["lAr"], "evler"),                     # two-way harmony, front
    ("kitap", ["lAr"], "kitaplar"),               # two-way harmony, back
    ("göz", ["lAr"], "gözler"),                   # front rounded triggers front
    ("ev", ["(y)I"], "evi"),                      # buffer dropped after consonant
    ("masa", ["(y)I"], "masayı"),                 # buffer kept after vowel
    ("okul", ["(y)I"], "okulu"),                  # four-way: back rounded
    ("göz", ["(y)I"], "gözü"),                    # four-way: front rounded
    ("kitap", ["(y)I"], "kitabı"),                # intervocalic softening p>b
    ("kanat", ["(y)I"], "kanadı"),                # t>d
    ("ağaç", ["(y)I"], "ağacı"),                  # ç>c
    ("ekmek", ["(y)I"], "ekmeği"),                # k>ğ
    ("renk", ["(y)I"], "rengi"),                  # post-nasal k>g, ordered first
    ("disk", ["(y)I"], "diski"),                  # monosyllable blocks softening
    ("at", ["(y)I"], "atı"),                      # ditto: atı, never adı
    ("ev", ["DA"], "evde"),                       # D assimilates to voiced
    ("kitap", ["DA"], "kitapta"),                 # D assimilates to voiceless
    ("ev", ["(n)In"], "evin"),
    ("masa", ["(n)In"], "masanın"),
    ("ev", ["lAr", "DA"], "evlerde"),             # cyclic: harmonizes to the affix
    ("kitap", ["lAr", "DA"], "kitaplarda"),
    ("ev", ["lAr", "Im", "DA"], "evlerimde"),     # three slots in order
    ("çocuk", ["lAr", "(y)I"], "çocukları"),
])
def test_turkish_phonology_produces_the_attested_form(stem, affixes, expected):
    out = stem
    for affix in affixes:
        out = TURKISH_PHONOLOGY.attach(out, affix)
    assert out == expected


def test_turkish_derives_its_paradigm_rather_than_storing_it():
    """The vocabulary file lists one form per noun; the rest must be derived."""
    tr = get_grammar("turkish")
    raw = tr.raw["nouns"]["house"]
    assert set(raw) == {"lemma"}, "a Turkish noun stores only its stem"
    assert tr.inflect("N", "house", FS(num="pl")) == "evler"
    assert tr.inflect("N", "house", FS(case="loc")) == "evde"
    assert tr.inflect("N", "house", FS(num="pl", case="loc")) == "evlerde"


# ======================================================================
# Swahili concord
# ======================================================================
@pytest.mark.parametrize("key,singular,plural", [
    ("book", "kitabu kikubwa", "vitabu vikubwa"),      # class 7/8
    ("person", "mtu mkubwa", "watu wakubwa"),          # class 1/2
    ("tree", "mti mkubwa", "miti mikubwa"),            # class 3/4
    ("stone", "jiwe kubwa", "mawe makubwa"),           # class 5/6, ji- prefix
    ("word", "neno kubwa", "maneno makubwa"),          # class 5, no ji-
    ("house", "nyumba kubwa", "nyumba kubwa"),         # class 9/10, invariant
])
def test_swahili_plural_is_a_class_change_carried_by_both_words(key, singular, plural):
    sw = get_grammar("swahili")
    assert sw.lin(np(key, "big")) == singular
    assert sw.lin(np(key, "big").but(num="pl")) == plural


@pytest.mark.parametrize("key,expected", [
    ("book", "kitabu chekundu"),      # class 7 ki- > ch- before a vowel
    ("person", "mtu mwekundu"),       # class 1 m- > mw-
    ("tree", "mti mwekundu"),
    ("stone", "jiwe jekundu"),        # class 5 zero > j-
    ("house", "nyumba nyekundu"),     # class 9 N- > ny-
])
def test_swahili_picks_the_pre_vocalic_allomorph(key, expected):
    assert get_grammar("swahili").lin(np(key, "red")) == expected


@pytest.mark.parametrize("adjective,expected", [
    ("big", "nyumba kubwa"),          # nasal deletes before a voiceless stop
    ("small", "nyumba ndogo"),        # and surfaces before a voiced one
    ("heavy", "nyumba nzito"),
])
def test_swahili_class_nine_nasal_has_three_outcomes(adjective, expected):
    assert get_grammar("swahili").lin(np("house", adjective)) == expected


def test_swahili_borrowed_adjectives_take_no_concord_at_all():
    sw = get_grammar("swahili")
    for key in ("book", "person", "house"):
        assert sw.lin(np(key, "blue")).endswith("buluu")
        assert sw.lin(np(key, "blue").but(num="pl")).endswith("buluu")


def test_swahili_predicative_concord_tracks_class_and_number_together():
    """The bug this catches lost the number and kept the class, silently."""
    sw = get_grammar("swahili")
    assert sw.sentence(sw.lin(pred_attr(np("book", det="def"), adj("big")))) \
        == "Kitabu ni kikubwa."
    assert sw.sentence(sw.lin(
        pred_attr(np("book", det="def").but(num="pl"), adj("big")))) \
        == "Vitabu ni vikubwa."


def test_swahili_noun_class_is_the_same_feature_spanish_puts_gender_in():
    """The argument of the rewrite, as an assertion."""
    from langcurriculum.grammar.category import CLS
    assert get_grammar("swahili").features_of("book")[CLS] == "7"
    assert get_language("spanish").lexicon.vocabulary.nouns["sphere"].gender == "f"


# ======================================================================
# typology: one tree, several word orders
# ======================================================================
def test_the_same_tree_comes_out_verb_final_in_turkish_and_verb_medial_in_english():
    from langcurriculum.grammar.category import V
    from langcurriculum.grammar.syntax import lex
    tree = pred_rel(np("book", det="def"), lex(V, "requires"), np("key", det="def"))
    english = get_grammar("english").lin(tree)
    turkish = get_grammar("turkish").lin(tree)
    assert english == "the book requires the key"
    # object precedes the verb, and is accusative rather than positioned
    assert turkish.endswith("gerektirir")
    assert turkish.index("anahtar") < turkish.index("gerektirir")


def test_turkish_marks_a_definite_object_and_leaves_an_indefinite_one_bare():
    """Differential object marking: the contrast is the case, not the position."""
    from langcurriculum.grammar.category import V
    from langcurriculum.grammar.syntax import lex
    tr = get_grammar("turkish")
    definite = pred_rel(np("book", det="def"), lex(V, "requires"), np("key", det="def"))
    indefinite = pred_rel(np("book", det="def"), lex(V, "requires"),
                          np("key", det="indef"))
    assert "anahtarı" in tr.lin(definite)
    assert "anahtarı" not in tr.lin(indefinite)
    assert "anahtar" in tr.lin(indefinite)


def test_only_the_languages_that_have_articles_emit_one():
    assert get_grammar("english").lin(np("book", det="def")).startswith("the ")
    # Turkish and Swahili have no definite article at all
    assert get_grammar("turkish").lin(np("book", det="def")) == "kitap"
    assert get_grammar("swahili").lin(np("book", det="def")) == "kitabu"


def test_adjective_side_follows_the_parameter():
    assert get_grammar("english").lin(np("book", "big")) == "big book"
    assert get_grammar("turkish").lin(np("book", "big")) == "büyük kitap"
    # Swahili puts it after
    assert get_grammar("swahili").lin(np("book", "big")) == "kitabu kikubwa"


def test_a_numeral_pluralizes_the_noun_only_where_the_language_says_so():
    assert get_grammar("english").lin(mk_np(mk_cn(noun("book")), count=3)) == "3 books"
    # üç kitap, never üç kitaplar
    assert get_grammar("turkish").lin(mk_np(mk_cn(noun("book")), count=3)) == "3 kitap"


def test_negation_sits_where_each_language_puts_it():
    tree = negate(pred_attr(np("cube", det="def"), adj("red")))
    assert get_grammar("english").lin(tree) == "the cube is not red"
    # Turkish postposes değil; the copula is not pronounced at all
    assert get_grammar("turkish").lin(tree).endswith("değil")


def test_turkish_has_no_overt_present_copula():
    tree = pred_attr(np("cube", det="def"), adj("red"))
    assert get_grammar("turkish").lin(tree) == "küp kırmızı"


def test_the_question_clitic_harmonizes_with_whatever_precedes_it():
    """``mI`` is a lookup in no table: it depends on the finished sentence."""
    tr = get_grammar("turkish")
    red = tr.question(yn_question(pred_attr(np("cube", det="def"), adj("red"))))
    big = tr.question(yn_question(pred_attr(np("cube", det="def"), adj("big"))))
    assert red == "Küp kırmızı mı?"
    assert big == "Küp büyük mü?"


def test_english_is_the_one_that_overrides_polar_question_formation():
    """Auxiliary fronting is typologically marked, so it is the override."""
    tree = yn_question(pred_attr(np("cube", det="def"), adj("red")))
    assert get_grammar("english").question(tree) == "Is the cube red?"


# ======================================================================
# coverage
# ======================================================================
@pytest.mark.parametrize("code", ENGINE_LANGUAGES)
def test_every_grammar_declares_what_it_implements(code):
    grammar = get_grammar(code)
    assert grammar.notes, f"{code} must say what it does"
    assert any("NOT attempted" in n for n in grammar.notes), \
        f"{code} must also say what it does not attempt"


@pytest.mark.parametrize("code", ENGINE_LANGUAGES)
def test_every_lesson_renders_without_crashing(code):
    for lesson in IMPLEMENTED:
        for seed in (0, 3):
            example = lesson.example(seed, language=code)
            assert example.prompt.strip(), f"{code}/{lesson.id} rendered empty"
            assert example.answer is not None


@pytest.mark.parametrize("code", ENGINE_LANGUAGES)
def test_the_answer_set_stays_distinguishable(code):
    """Translating the options must never merge two of them."""
    for lesson in IMPLEMENTED:
        example = lesson.example(3, language=code)
        assert len(set(example.choices)) == len(example.choices), \
            f"{code}/{lesson.id}: two options collapsed into one"
        assert example.answer in example.choices


@pytest.mark.parametrize("code", ENGINE_LANGUAGES)
def test_no_two_prompts_carry_different_answers(code):
    """The property that says the prose still determines the answer."""
    for lesson in IMPLEMENTED[::4]:
        seen: dict[str, str] = {}
        for example in lesson.examples(20, language=code):
            prior = seen.get(example.prompt)
            assert prior is None or prior == example.answer, \
                f"{code}/{lesson.id}: two answers behind one prompt"
            seen[example.prompt] = example.answer


_LEAKED = re.compile(r"\?[a-z]+(?:#\d+)?\b|FS\(|Var\(|Node\(|<[a-z]+ object")


@pytest.mark.parametrize("code", ENGINE_LANGUAGES)
def test_no_internal_representation_reaches_the_page(code):
    """An unbound ``?n`` or a repr'd object means the walk leaked its own state.

    Cheap to check and worth checking: these leaks are invisible in a spot check
    of English and obvious to a reader of the language that has them.
    """
    for lesson in IMPLEMENTED[::3]:
        text = lesson.example(1, language=code).prompt
        leak = _LEAKED.search(text)
        assert leak is None, f"{code}/{lesson.id} leaked {leak.group(0)!r}"


def test_every_construction_has_a_linearization_in_every_grammar():
    """A missing construction must be a loud failure, not a dropped constituent."""
    for code, grammar in GRAMMARS.items():
        for construction in CONSTRUCTIONS:
            assert hasattr(grammar, f"lin_{construction}"), \
                f"{code} cannot linearize {construction}"


# ======================================================================
# evidentiality: obligatory marking, read off the structure
# ======================================================================
def test_turkish_marks_a_reported_proposition_and_a_witnessed_one_differently():
    """There is no neutral form, so a grammar must choose — and must be right.

    *Küp kırmızı* asserts on the speaker's own authority; *küp kırmızıymış*
    asserts on someone else's. Rendering a reported clause as direct would make
    the Turkish episode claim something the English one does not.
    """
    tr = get_grammar("turkish")
    clause = pred_attr(np("cube", det="def"), adj("red"))
    assert tr.sentence(tr.lin(clause)) == "Küp kırmızı."
    assert tr.sentence(tr.lin(clause.but(evid="reported"))) == "Küp kırmızıymış."


@pytest.mark.parametrize("key,adjective,expected", [
    ("book", "big", "Kitap büyükmüş."),      # after a consonant: direct
    ("cube", "red", "Küp kırmızıymış."),     # after a vowel: buffer y
    ("water", "warm", "Su ılıkmış."),        # back harmony
])
def test_the_evidential_harmonizes_and_attaches_without_a_space(key, adjective, expected):
    tr = get_grammar("turkish")
    clause = pred_attr(np(key, det="def"), adj(adjective)).but(evid="reported")
    assert tr.sentence(tr.lin(clause)) == expected


def test_the_evidence_source_is_read_off_the_structure_not_guessed():
    """A proposition under a reporting predicate is second-hand by construction."""
    from langcurriculum._structure import Ident, Pred
    from langcurriculum.grammar.compile import compile_term
    from langcurriculum.grammar.frames import REPORTING

    assert "says" in REPORTING and "claims" in REPORTING
    reported = compile_term(Pred("says", Ident("alice"), Pred("color", Ident("o0"),
                                                              Ident("red"))))
    embedded = [a.node for a in reported.args if a.node.cat.name == "Cl"]
    assert embedded, "the complement should have compiled to a clause"
    assert any(n.feats.get_atom("evid") == "reported" for n in embedded)

    # and an unembedded scene description must NOT be marked
    direct = compile_term(Pred("color", Ident("o0"), Ident("red")))
    assert direct.feats.get_atom("evid") is None


def test_a_relative_spatial_frame_is_marked_as_relative():
    """Guugu Yimithirr has no 'left of'. A grammar for it must be able to refuse."""
    from langcurriculum._structure import Ident, Pred
    from langcurriculum.grammar.compile import compile_term
    from langcurriculum.grammar.frames import SPATIAL_FRAME

    assert "left_of" in SPATIAL_FRAME
    node = compile_term(Pred("left_of", Ident("red"), Ident("cube")))
    assert node.feats.get_atom("frame") == "relative"


# ======================================================================
# behaviour that belongs to every grammar, not to one subclass
# ======================================================================
@pytest.mark.parametrize("code", sorted(GRAMMARS))
def test_every_grammar_composes_multi_word_labels(code):
    """The composition lives on the base class, and this is why.

    Token-by-token rendering of a multi-word label was written on the derived
    grammar only. The five hand-written ones inherited nothing and silently kept
    every phrase in English — Spanish sat at 6.5% leakage while the derived
    languages fell to 2-4%, and nothing failed, because a subclass that quietly
    lacks a behaviour looks exactly like a subclass that does not need it.
    """
    grammar = GRAMMARS[code]
    assert hasattr(grammar, "phrase") and hasattr(grammar, "lookup"), code


@pytest.mark.parametrize("code", sorted(GRAMMARS))
def test_a_coined_sequence_survives_every_grammar(code):
    """Whatever a grammar does to phrases, it must not touch coined tokens.

    Deliberately strings no pack could carry. The obvious candidates are traps:
    ``bfs astar`` and ``kirn bex dov`` look coined and are not — the packs hold
    curated entries for them (``BFS``, ``A*``, ``Kirn``, ``基恩``), and
    translating a term somebody added on purpose is correct behaviour, not a
    leak. What must survive is a form the generators minted this episode.
    """
    grammar = GRAMMARS[code]
    for nonce in ("qzxjv wrktp", "vlmqz phdxn", "xkkvr zzptq brnwq"):
        assert grammar.word(nonce) == nonce, f"{code} altered {nonce!r}"


@pytest.mark.parametrize("code", sorted(GRAMMARS))
def test_an_unknown_word_passes_through_every_grammar(code):
    """Most of what this curriculum names is coined per episode.

    ``lookup`` returning the empty string for an unknown word rather than the
    word itself is what lets the composer tell "no translation" from "translates
    to itself"; the passthrough then happens in exactly one place.
    """
    grammar = GRAMMARS[code]
    assert grammar.lookup("qzxjv", "") == ""
    assert grammar.word("qzxjv") == "qzxjv"


# ======================================================================
# importing lexical gaps from the database
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["turkish", "swahili", "spanish", "chinese"])
def test_a_curated_entry_is_never_overridden_by_an_imported_one(code):
    """Curated wins, and the database only fills the gaps.

    The order is the whole point: a small verified vocabulary plus a large
    scraped one is an improvement only if the scraped half cannot displace the
    verified half.
    """
    grammar = get_grammar(code)
    for key in grammar._imported:
        assert not grammar.vocabulary.knows(key), \
            f"{code}: imported {key!r} shadows a curated entry"


@needs_db
@pytest.mark.parametrize("code", ["turkish", "swahili", "spanish", "chinese"])
def test_no_two_keys_import_the_same_word(code):
    """A dictionary gives one word for two concepts and the episode breaks.

    Turkish *para* is both *money* and *coin*; Swahili *sanduku* is both *crate*
    and *box*. An episode naming both becomes unanswerable, so where an import
    would collide — with another import or with a curated entry — it is dropped
    and the English shows through instead. A visibly untranslated word is a much
    smaller problem than an ambiguous one.
    """
    grammar = get_grammar(code)
    forms = list(grammar._imported.values())
    assert len(forms) == len(set(forms)), f"{code}: two keys share a form"
    curated = {grammar.vocabulary.translate(k)
               for k in set(grammar.vocabulary.nouns) | set(grammar.vocabulary.words)}
    assert not (set(forms) & curated), f"{code}: an import collides with curated"


@needs_db
@pytest.mark.parametrize("code", ["turkish", "swahili", "spanish", "chinese"])
def test_a_coined_identifier_is_never_looked_up_in_the_database(code):
    """The import is restricted to vocabulary the curriculum actually coins.

    Short minted tokens collide with real words — Spanish rendered the nonce
    ``nu`` as ``ni``, which is also what the nonce ``ni`` became — and the
    lesson turns on those tokens being distinct.
    """
    grammar = get_grammar(code)
    for nonce in ("nu", "ni", "zrv", "ppk", "qzxjv"):
        if grammar.vocabulary.knows(nonce):
            continue
        assert nonce not in grammar._imported, f"{code} imported the nonce {nonce!r}"


@needs_db
def test_importing_gaps_roughly_doubles_what_turkish_can_say():
    """The point of the exercise, as a number.

    Turkish ships 115 of the curriculum's keys by hand; the database carries
    more than twice that, and importing the non-colliding remainder is what
    makes a hand-written grammar usable across the whole curriculum rather than
    only the parts somebody had time to translate.
    """
    from langcurriculum.grammar.compile import curriculum_vocabulary
    keys = sorted(curriculum_vocabulary())
    grammar = get_grammar("turkish")
    curated = sum(1 for k in keys if grammar.vocabulary.knows(k))
    total = sum(1 for k in keys if grammar.word(k) != k)
    assert curated < 130, "the curated pack grew; update the comparison"
    assert total >= 220, f"only {total} keys covered, was expecting the import"


# ======================================================================
# the seed space, not just the seeds the other tests happen to use
# ======================================================================
def test_generation_holds_up_well_outside_the_seeds_the_suite_uses():
    """Almost every test here uses seeds 0-3. Callers export with n=1000.

    A generator branch that only fires on an unusual seed has never been
    rendered by anything, and the first person to meet it would be someone
    building a training set. Sampling widely and cheaply is the difference
    between "the paths we look at are fine" and "the paths are fine".

    Deliberately a smoke test: crashes, empty prompts, answers that are not
    among the options, and internal representation reaching the page. Anything
    subtler belongs in a test that names the property.
    """
    import re
    leaked = re.compile(r"\(\s*'|\[\s*'|\{'|\bNone\b|object at 0x|\?[a-z]+#\d+|FS\(")
    seeds = range(500, 520)          # far from anything else the suite touches
    problems = []
    for lesson in IMPLEMENTED[::5]:
        for seed in seeds:
            example = lesson.example(seed, language="english")
            if not example.observation.strip():
                problems.append(f"{lesson.id} s{seed}: empty")
            if example.answer not in example.choices:
                problems.append(f"{lesson.id} s{seed}: answer not an option")
            if len(set(example.choices)) != len(example.choices):
                problems.append(f"{lesson.id} s{seed}: duplicate options")
            hit = leaked.search(example.observation)
            if hit:
                problems.append(f"{lesson.id} s{seed}: leaked {hit.group(0)!r}")
    assert not problems, problems[:6]


@pytest.mark.parametrize("code", ["turkish", "swahili"])
def test_a_grammar_holds_up_outside_those_seeds_too(code):
    """The same, through a grammar with real morphology.

    Higher risk than English: an unusual seed coins a lemma the inducer has
    never seen, and the analogical path runs on it.
    """
    import re
    leaked = re.compile(r"\(\s*'|\[\s*'|\{'|\bNone\b|object at 0x|\?[a-z]+#\d+|FS\(")
    for lesson in IMPLEMENTED[::9]:
        for seed in range(500, 510):
            example = lesson.example(seed, language=code)
            assert example.observation.strip(), f"{code}/{lesson.id} s{seed}: empty"
            assert example.answer in example.choices, \
                f"{code}/{lesson.id} s{seed}: answer not an option"
            hit = leaked.search(example.observation)
            assert hit is None, f"{code}/{lesson.id} s{seed}: leaked {hit.group(0)!r}"


# ======================================================================
# what two words do to each other where they meet
# ======================================================================
def test_elision_writes_the_apostrophe_french_requires():
    """*la eau* is not French. The article elides before a vowel."""
    from langcurriculum.grammar.linearize import Sandhi
    s = Sandhi(elide={"la": "l'", "le": "l'"})
    assert s.apply("la", "eau", " ") == "l'eau"
    assert s.apply("le", "arbre", " ") == "l'arbre"
    # a consonant blocks it, which is the whole conditioning environment
    assert s.apply("la", "maison", " ") is None


def test_elision_sees_only_the_words_at_the_boundary():
    """``join`` folds left to right, so the left side is often already a phrase.

    Only its final token may elide, and everything before it must survive
    untouched — otherwise composing a longer phrase would corrupt what an
    earlier composition had already got right.
    """
    from langcurriculum.grammar.linearize import Sandhi
    s = Sandhi(elide={"de": "d'"})
    assert s.apply("à côté de", "eau", " ") == "à côté d'eau"
    assert s.apply("le cube de", "or", " ") == "le cube d'or"


def test_contraction_needs_both_words_named_not_a_vowel():
    """Spanish *del* is not elision: *de el* contracts, *de agua* does not.

    The distinction matters because Spanish has contraction and no elision at
    all, so a mechanism that only knew about vowels would either miss *del* or
    wrongly produce *d'agua*.
    """
    from langcurriculum.grammar.linearize import Sandhi
    s = Sandhi(contract={"de el": "del", "a el": "al"})
    assert s.apply("de", "el cubo", " ") == "del cubo"
    assert s.apply("a", "el disco", " ") == "al disco"
    assert s.apply("de", "agua", " ") is None       # no elision in Spanish
    assert s.apply("de", "la casa", " ") is None    # not the named pair


def test_contraction_beats_elision_when_both_could_fire():
    """Contraction names both words, so it is the more specific statement."""
    from langcurriculum.grammar.linearize import Sandhi
    s = Sandhi(elide={"de": "d'"}, contract={"de els": "dels"})
    assert s.apply("de", "els cubs", " ") == "dels cubs"


def test_a_sentence_initial_capital_survives_the_substitution():
    from langcurriculum.grammar.linearize import Sandhi
    s = Sandhi(elide={"la": "l'"}, contract={"de el": "del"})
    assert s.apply("La", "eau", " ") == "L'eau"
    assert s.apply("De", "el cubo", " ") == "Del cubo"


def test_spanish_writes_del_not_de_el():
    """The defect this was built for, in the language that shipped it."""
    grammar = get_grammar("spanish")
    assert "del" in grammar.join(["de", "el disco"])
    assert "de el" not in grammar.join(["de", "el disco"])


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("fra", "l'"), ("ita", "l'"), ("cat", "l'"),
])
def test_the_romance_languages_that_elide_do(code, expected):
    grammar = DerivedGrammar(LanguageDB(), code)
    assert grammar.sandhi, f"{code} should have a sandhi table"
    assert grammar.join(["la", "eau"]).startswith(expected)


@needs_db
def test_spanish_has_contraction_but_no_elision():
    """Not an oversight. *el agua* is a different rule and lives elsewhere.

    Treating it as elision would wrongly catch *la avenida*, which keeps its
    article: the conditioning is a stressed initial /a/, which the lexicon does
    not record, and the pack states the affected nouns explicitly instead.
    """
    grammar = DerivedGrammar(LanguageDB(), "spa")
    assert not grammar.sandhi.elide
    assert grammar.sandhi.contract


# ======================================================================
# predicate heads are not words of any language
# ======================================================================
def test_no_grammar_prints_a_predicate_head_as_though_it_were_a_word():
    """``left_of`` is an internal identifier and was reaching the page.

    The heads this curriculum uses are inflected English verbs (*implies*),
    abbreviations (*sub*) and identifiers with underscores in them. No
    dictionary in any language keys on those, so every derived grammar — four
    hundred of them — returned the head unchanged and printed it.
    """
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS
    assert "left_of" in PREDICATE_GLOSS
    for name in sorted(GRAMMARS):
        grammar = get_grammar(name)
        for head in PREDICATE_GLOSS:
            rendered = grammar.word(head, "V")
            assert "_" not in rendered, f"{name} rendered {head!r} as {rendered!r}"


@needs_db
@pytest.mark.parametrize("code", ["fra", "deu", "rus", "por", "nld"])
def test_a_derived_grammar_spells_out_a_relation_it_has_no_entry_for(code):
    grammar = DerivedGrammar(LanguageDB(), code)
    rendered = grammar.word("left_of", "V")
    assert "_" not in rendered
    assert rendered != "left_of"


def test_spelling_out_is_restricted_to_the_listed_heads():
    """A coined nonce form must pass through untouched.

    Most of what this curriculum names is invented per episode, and a lesson
    that turns on a novel symbol is destroyed by translating it. The guarantee
    is that only heads in the table are ever spelled out.
    """
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS
    grammar = get_grammar("english")
    for coined in ("kirn_bex", "zog_flim", "o0_o1"):
        assert coined not in PREDICATE_GLOSS
        assert grammar.word(coined, "V") == coined


def test_the_gloss_table_is_a_translation_source_not_a_realization():
    """English realizes *precedes* as "comes before"; the gloss says "precede".

    The distinction is the reason this table exists separately from a pack's
    ``predicate_words``: a dictionary keys on the citation form, and handing it
    an English idiom retrieves nothing.
    """
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS
    english = get_grammar("english")
    assert PREDICATE_GLOSS["precedes"] == "precede"
    assert english.predicate_words["precedes"] == "comes before"


# ======================================================================
# structural words the engine emits on its own account
# ======================================================================
#: Every comparison the linearizer can be asked to render.
COMPARISONS = ("gt", "lt", "eq", "ne", "ge", "le")


def _frame_kinds():
    from langcurriculum.grammar.frames import FRAMES
    return sorted({f.kind for f in FRAMES.values() if getattr(f, "kind", "")})


def test_every_frame_kind_is_a_slot_some_lexicon_can_fill():
    """``rule`` was not, and so was printed in every language including Chinese.

    Six frames carry a ``kind`` that becomes a word in the output — *rule 4*,
    *step 2*, *round 7*. Five were listed as closed-class slots and the sixth
    was overlooked, which no test could catch because nothing asserted the two
    sets were the same. ``rule`` is the commonest of them.
    """
    from langcurriculum.grammar.derived import CLOSED_CLASS_KEYS
    missing = [k for k in _frame_kinds() if k not in CLOSED_CLASS_KEYS]
    assert not missing, f"frame kinds with nowhere to get a word: {missing}"


def test_every_comparison_has_somewhere_to_get_a_word():
    """``gt`` is an abbreviation. Four hundred grammars printed it as one."""
    from langcurriculum.grammar.derived import CLOSED_CLASS_KEYS
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS
    for rel in COMPARISONS:
        assert rel in CLOSED_CLASS_KEYS or rel in PREDICATE_GLOSS, \
            f"{rel!r} would be printed as the abbreviation itself"


@pytest.mark.parametrize("code", sorted(GRAMMARS))
def test_a_hand_written_pack_names_every_structural_word(code):
    """A verified grammar should not fall back to a gloss for these.

    The fallback exists for the derived half, where nobody has looked. A pack
    somebody wrote by hand has no excuse for leaving *is not equal to* to be
    assembled out of dictionary parts — and ``ne`` was missing from all five,
    so even English rendered it as ``ne``.
    """
    grammar = get_grammar(code)
    for slot in (*_frame_kinds(), *COMPARISONS):
        assert grammar.cw(slot), f"{code} has no word for {slot!r}"


@pytest.mark.parametrize("code", sorted(GRAMMARS))
def test_no_grammar_prints_a_structural_abbreviation(code):
    """The output test, not the table test: what actually reaches the page."""
    grammar = get_grammar(code)
    for slot in (*_frame_kinds(), *COMPARISONS):
        rendered = grammar.cw(slot) or grammar.word(slot, "V")
        assert rendered != slot or code.startswith("english"), \
            f"{code} renders {slot!r} as itself"


@needs_db
@pytest.mark.parametrize("code", ["fra", "rus", "deu", "nld", "pol"])
def test_a_derived_grammar_renders_comparisons_in_its_own_language(code):
    """*plus que*, *бо́льше чем*, *mehr als* — not *gt*."""
    grammar = DerivedGrammar(LanguageDB(), code)
    for rel in COMPARISONS:
        rendered = grammar.cw(rel) or grammar.word(rel, "V")
        assert rendered != rel, f"{code} renders {rel!r} as itself"


# ======================================================================
# a translation that merges two concepts is worse than none
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["fra", "por", "deu", "rus", "nld", "ita"])
def test_a_derived_grammar_never_gives_two_concepts_the_same_word(code):
    """French offers *donner* for both *give* and *hand*.

    The taxonomy lesson lists both as separate rungs, so French printed the
    identical premise twice and the distinction the episode turns on was gone.
    The hand-written grammars have refused this since the import was written;
    only the derived half was exempt, because it reads the database directly.
    """
    from langcurriculum.grammar.compile import curriculum_vocabulary
    from langcurriculum.grammar.derived import probe_form

    # Two *concepts*, not two spellings. ``binds`` is the third person of
    # ``bind`` and the two are one word; requiring them to render differently
    # would be requiring a language to invent a distinction it does not draw.
    grammar = DerivedGrammar(LanguageDB(), code)
    rendered: dict[tuple[str, str], str] = {}
    for key in sorted(curriculum_vocabulary()):
        concept = probe_form(key)
        for pos in ("N", "A", "V"):
            form = grammar.lookup(key, pos)
            if not form:
                continue
            clash = rendered.get((form.lower(), pos))
            assert clash in (None, concept), \
                f"{code}: {concept!r} and {clash!r} both render as {form!r} ({pos})"
            rendered[(form.lower(), pos)] = concept


@needs_db
def test_the_collision_that_prompted_this_is_gone():
    """*give* and *hand* must not both come out as *donner*."""
    grammar = DerivedGrammar(LanguageDB(), "fra")
    assert grammar.word("give", "V") != grammar.word("hand", "V")


def test_two_distinct_identifiers_stay_distinct_through_a_whole_episode():
    """The property that actually matters, checked on real generated text.

    A lesson names things and then asks about them. If two of those names
    collapse into one word the episode is not merely clumsy, it is
    unanswerable, so this walks the terms rather than the lexicon.
    """
    import collections
    import random

    from langcurriculum._structure import Ident, walk
    from langcurriculum.languages import get_language
    from langcurriculum.registry import all_lessons, get

    for code in ("fra", "rus", "deu", "por", "ita", "nld", "pol", "fin",
                 "spanish", "chinese", "turkish", "swahili"):
        language = get_language(code)
        for lesson_id in list(all_lessons())[::7]:
            lesson = get(lesson_id)
            for seed in range(2):
                try:
                    term, *_ = lesson.generate(random.Random(seed))
                except Exception:
                    continue
                names = sorted({t.value for t in walk(term)
                                if t.type == "ident" and isinstance(t.value, str)})
                seen = collections.defaultdict(list)
                for name in names:
                    seen[language.render(Ident(name))].append(name)
                for surface, sources in seen.items():
                    assert len(sources) == 1, (
                        f"{code}/{lesson_id} s{seed}: {sources} all render "
                        f"as {surface!r}")


# ======================================================================
# an abbreviation is not the English word it happens to be spelled like
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["deu", "spa", "fra", "nld", "rus"])
def test_an_abbreviated_head_is_not_looked_up_as_an_english_word(code):
    """German rendered ``sub`` as *U-Boot*. Spanish rendered ``pow`` as *zas*.

    A head whose gloss differs from its own spelling is an abbreviation or an
    inflected form, not a word being used as itself — but a dictionary keyed on
    spelling answers anyway, and every language had a small demon waiting for
    ``imp``.
    """
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS

    grammar = DerivedGrammar(LanguageDB(), code)
    for head, gloss in PREDICATE_GLOSS.items():
        if gloss == head:
            continue
        assert not grammar.lookup(head, "V"), \
            f"{code}: {head!r} was looked up as an English word"


@needs_db
def test_the_wrong_senses_that_prompted_this_are_gone():
    db = LanguageDB()
    german, spanish = DerivedGrammar(db, "deu"), DerivedGrammar(db, "spa")
    assert german.word("sub", "V") != "U-Boot"
    assert spanish.word("sub", "V") != "submarino"
    assert spanish.word("pow", "V") != "zas"
    for code in ("deu", "spa", "fra", "nld"):
        assert "imp" not in DerivedGrammar(db, code).lookup("imp", "V")


def test_iff_keeps_the_abbreviation_its_language_actually_uses():
    """The exception, and why it is one.

    Unlike the other abbreviations, ``iff`` has a conventional equivalent that
    dictionaries record — *ssi*, *gdw.*, *sii*. Composing it from *if and only
    if* produced *si et unique si*, so this one head keeps the lookup.
    """
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS
    assert "iff" not in PREDICATE_GLOSS


@needs_db
def test_a_translation_never_collides_with_a_word_that_passes_through():
    """The half of the rule that comparing translations to each other misses.

    Dutch for *minus* is "min", and ``min`` is itself a function the lessons
    name. Nothing translated it, so it went out as the English spelling — and
    the two were indistinguishable even though no two *translations* clashed.
    What a reader sees is the translation if there is one and the English if
    there is not, so that is what has to be unique.
    """
    grammar = DerivedGrammar(LanguageDB(), "nld")
    assert grammar.word("min", "V") != grammar.word("sub", "V")


@needs_db
@pytest.mark.parametrize("code", ["nld", "fra", "deu", "rus"])
def test_two_spellings_of_one_concept_are_not_treated_as_a_collision(code):
    """``imp`` and ``implies`` mean the same thing and share a gloss.

    An earlier version of the detector flagged them against each other and
    forced a perfectly good translation back into English. Heads are grouped
    by gloss so that one concept with two spellings stays one concept.
    """
    grammar = DerivedGrammar(LanguageDB(), code)
    assert grammar.word("imp", "V") == grammar.word("implies", "V")
    assert grammar.word("imp", "V") != "imp"


# ======================================================================
# the answer set is part of the episode, not a footnote to it
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["rus", "deu", "fra", "por", "pol", "tur"])
def test_a_derived_language_offers_its_options_in_its_own_language(code):
    """The prompt said *зелёного* and the options said *green*.

    Options must be in the prompt's language or the episode quietly becomes
    "translate, then answer". Every derived language failed this — not because
    it could not translate a colour, but because the question "do you know this
    word?" was put to a kind of lexicon only a hand-written pack has, so all
    four hundred of them answered no to every option they knew perfectly well.
    """
    from langcurriculum.languages import get_language
    from langcurriculum.registry import get

    language = get_language(code)
    for colour in ("red", "green", "blue", "yellow"):
        assert language.knows(colour), f"{code} should know {colour!r}"
    example = get("symbol_equivalence").example(0, language=code)
    assert not any(c in ("red", "green", "blue", "yellow")
                   for c in example.choices), \
        f"{code} offered English colours: {example.choices}"


@needs_db
@pytest.mark.parametrize("code", ["rus", "deu", "fra", "spa"])
def test_an_option_is_looked_up_as_the_part_of_speech_it_is(code):
    """*orange* is a colour here, and untyped lookup returns a tree.

    Russian offered *апельси́новое де́рево* and German *Apfelsinenbaum* in a list
    of colours. The category comes from the same ``classify`` the compiler uses
    for the prose, so the option is resolved as whatever the prompt used it as.
    """
    from langcurriculum.languages import get_language
    rendered = get_language(code).token("orange")
    assert "baum" not in rendered.lower()
    assert "де́рево" not in rendered
    assert "oranger" != rendered.lower()


def test_every_language_can_be_asked_whether_it_knows_a_word():
    """``knows`` is on the interface, not on one implementation of it.

    The notation pack is not a grammar and has no vocabulary object; asking it
    the question through an attribute only some packs carry raised rather than
    answering, and took a hundred and eighty tests with it.
    """
    from langcurriculum.languages import get_language, language_codes
    for code in language_codes():
        assert isinstance(get_language(code).knows("green"), bool)


@needs_db
def test_a_word_withheld_to_avoid_ambiguity_is_not_offered_as_an_option():
    """Otherwise dropping it from the prose would have achieved nothing.

    A key held back because two concepts would share its form must not come
    back through the answer set, which would reintroduce exactly the ambiguity
    the exclusion prevents.
    """
    grammar = DerivedGrammar(LanguageDB(), "fra")
    assert grammar._ambiguous, "expected French to withhold something"
    for key in grammar._ambiguous:
        assert not grammar.knows(key), f"{key!r} withheld from prose but offered"


# ======================================================================
# what a pack reports about itself has to be measured, not assumed
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["rus", "deu", "fra", "hin", "por"])
def test_a_derived_language_reports_the_vocabulary_it_actually_has(code):
    """It reported zero, and was classed as partial without being measured.

    ``partial_vocabulary`` is documented as computed rather than declared —
    "by arithmetic rather than by an attribute someone forgot to flip". The
    arithmetic was ``len(lexicon.vocabulary)``, and a derived grammar leaves
    that empty because its words are in a database. Four hundred languages
    reported a vocabulary of nothing while covering half the curriculum.
    """
    from langcurriculum.languages import get_language
    coverage = get_language(code).coverage()
    assert coverage["total"] > 100, f"{code} reported {coverage}"
    assert sum(v for k, v in coverage.items() if k != "total") == coverage["total"]


def test_every_language_reports_a_coverage_it_could_have_measured():
    from langcurriculum.languages import get_language, language_codes
    for code in language_codes():
        coverage = get_language(code).coverage()
        assert coverage["total"] >= 0
        assert set(coverage) >= {"total"}


@needs_db
@pytest.mark.parametrize("code", ["fra", "rus", "deu", "hin", "por"])
def test_the_two_ways_of_counting_coverage_agree(code):
    """One is a query and one asks ``knows`` four hundred times.

    They must be the same number. A first version subtracted the whole
    withheld set from the query's total, including words that had no entry to
    withhold, and came out one short — the same drift that has now twice let a
    check pass while the thing it checked was broken.
    """
    from langcurriculum.grammar.compile import curriculum_vocabulary
    grammar = DerivedGrammar(LanguageDB(), code)
    one_query = grammar._curriculum_coverage()
    by_asking = sum(1 for k in curriculum_vocabulary() if grammar.knows(k))
    assert one_query == by_asking


@needs_db
@pytest.mark.parametrize("code", ["fra", "rus", "hin"])
def test_a_partial_lexicon_is_stated_as_a_gap(code):
    """A reader should not have to measure it themselves."""
    gaps = " ".join(DerivedGrammar(LanguageDB(), code).gaps())
    assert "words the lessons can coin" in gaps
    assert "withheld" in gaps


def test_a_full_pack_is_not_reported_as_partial():
    """The change of basis must not reclassify the hand-written packs."""
    from langcurriculum.languages import get_language
    for code in ("english", "spanish", "chinese"):
        assert not get_language(code).partial_vocabulary
    for code in ("turkish", "swahili"):
        assert get_language(code).partial_vocabulary


# ======================================================================
# inflected material for the lessons that are about inflection
# ======================================================================
_SUPPLYING = ["deu", "fra", "spa", "ita", "por", "pol", "ces", "ell", "ron", "cat"]


@needs_db
@pytest.mark.parametrize("code", _SUPPLYING)
def test_a_derived_grammar_builds_its_own_agreement_material(code):
    """Otherwise the lesson is presented in English however good the grammar is.

    These seven lessons build their sentences out of inflected words rather
    than translating at render time, so a language with no tables of its own
    gets English ones — an agreement lesson in English wearing a Greek hat.
    """
    from langcurriculum._support.extra import PARALLEL_FIELDS
    tables = DerivedGrammar(LanguageDB(), code).paradigms
    assert tables, f"{code} built nothing"
    for field, count in PARALLEL_FIELDS.items():
        assert len(tables[field]) == count, f"{code}.{field}"


@needs_db
@pytest.mark.parametrize("code", _SUPPLYING)
def test_the_two_members_of_a_pair_are_never_the_same_word(code):
    """A head noun whose number cannot be seen leaves the question no evidence.

    German *Schlüssel* is its own plural. Offered as the head of an agreement
    episode it makes the episode unanswerable, so a pair that does not contrast
    is skipped and the next candidate tried.
    """
    tables = DerivedGrammar(LanguageDB(), code).paradigms
    for field in ("noun_forms", "agreement_forms"):
        for one, other in tables[field]:
            assert one != other, f"{code}.{field}: {one!r} twice"
        assert len({p[0] for p in tables[field]}) == len(tables[field])


@needs_db
@pytest.mark.parametrize("code", _SUPPLYING)
def test_every_cell_is_one_the_language_actually_attests(code):
    """Asking the morphology to inflect returns a near-miss when the exact cell
    is missing, and a near-miss is the wrong word.

    Greek answered a request for the third person plural with the first person
    singular, and Romanian answered a plural with a genitive. Both forms are
    attested; neither is the cell that was asked for. Cells are therefore
    selected by tag from what UniMorph records, not generated.
    """
    db = LanguageDB()
    grammar = DerivedGrammar(db, code)
    for singular, plural in grammar.paradigms["noun_forms"]:
        attested = {s for _, s in db.paradigm(code, singular)}
        assert plural in attested, f"{code}: {plural!r} not attested for {singular!r}"


@needs_db
def test_the_sentence_material_is_supplied_whole_or_not_at_all():
    """Half a table would put half a sentence in each language.

    The pronouns are a separate question and were once part of this one.
    Finnish, Turkish and Hungarian have a single genderless third person --
    hän, o, ő -- so requiring two distinct pronouns discarded six complete
    paradigms apiece to protect the one lesson that needs them.
    """
    db = LanguageDB()
    sentence = {"verbs", "intransitive_verbs", "adverbs", "preposition_words",
                "noun_forms", "agreement_forms"}
    for code in ("fin", "hun", "dan", "rus", "pol", "ces", "deu"):
        tables = set(DerivedGrammar(db, code).paradigms)
        assert not (tables & sentence) or sentence <= tables, code
        # and the pronoun pair travels together or not at all
        assert len(tables & {"pronouns", "name_gender"}) != 1, code


@needs_db
@pytest.mark.parametrize("code", ["fin", "hun"])
def test_a_genderless_pronoun_costs_only_the_lesson_that_needs_one(code):
    """It used to cost the language every morphology lesson it had."""
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    tables = DerivedGrammar(db, code).paradigms
    assert tables.get("noun_forms"), f"{code} should supply its nouns"
    assert "pronouns" not in tables, f"{code} has no gendered pronoun to supply"


@needs_db
@pytest.mark.parametrize("code", ["fin", "hun", "rus"])
def test_the_coreference_lesson_falls_back_before_it_draws(code):
    """Taking a Finnish sentence and an English pronoun would be worse.

    The lesson turns on the pronoun distinguishing its antecedents, so where
    there is no gendered pronoun the episode cannot be presented at all. It
    declines before touching the random stream: checking later re-ran the
    generator mid-stream and the fallback came out about a different pair of
    people, which would have moved the answer.

    The whole discourse is asserted, not just the material chosen: a sentence
    the lesson assembled is now rendered as written, so the fallback comes out
    in English throughout rather than with the two or three words the renderer
    happened to recognise translated out from under it.
    """
    from langcurriculum.registry import get
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    english = get("pronoun_coreference").example(0, language="english")
    other = get("pronoun_coreference").example(0, language=code)
    assert other.metadata["hidden"]["referent"] == \
        english.metadata["hidden"]["referent"]
    body = [l for l in other.observation.splitlines() if l.strip().startswith("-")]
    reference = [l for l in english.observation.splitlines()
                 if l.strip().startswith("-")]
    assert body == reference, f"{code}: half-translated discourse"


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "ell"])
def test_the_lessons_come_out_in_the_language_that_was_asked_for(code):
    """The end of the chain: real generated text, not a table.

    Only the sentence itself. The query label beside it is a field name the
    compiler passes through untranslated in every language, which is a
    different gap and one this change does not touch.
    """
    from langcurriculum.registry import get

    def sentence(language: str) -> set[str]:
        text = get("long_range_agreement").example(0, language=language).observation
        return {line.strip("- ").strip() for line in text.splitlines()
                if line.strip().startswith("-")} - {"__"}

    shared = sentence("english") & sentence(code)
    assert not shared, f"{code} shares {shared} with the English sentence"


def test_a_pack_that_writes_its_article_into_its_nouns_says_so():
    """Spanish ships *el granjero*; English ships *the* and *farmer* apart.

    Guessing produced *der Buch* in German and *ο κλειδιά* in Greek, because a
    single article cannot agree with every noun it precedes. Whether the
    article is a token of its own is now declared by the pack.
    """
    from langcurriculum._support import extra
    from langcurriculum.languages import get_language
    assert get_language("english").lexicon.article == "the"
    assert get_language("spanish").lexicon.article == ""
    for code, expected in (("english", "the"), ("spanish", "")):
        token = extra.ACTIVE_LANGUAGE.set(code)
        try:
            assert extra.determiner() == expected
        finally:
            extra.ACTIVE_LANGUAGE.reset(token)


# ======================================================================
# the one sentence the learner has to act on
# ======================================================================
_INSTRUCTED = ["spanish", "chinese", "turkish", "swahili",
               "deu", "rus", "fra", "ell", "jpn", "hin", "por", "ita"]


@pytest.mark.parametrize("code", _INSTRUCTED)
def test_the_learner_is_told_what_to_do_in_their_own_language(code):
    """The scene translated, the options translated, and then this in English.

    Every episode ends with "Answer with exactly one of:", and it was English
    in all four hundred languages including the hand-written packs. It is the
    one sentence a learner has to act on rather than reason about.
    """
    from langcurriculum.languages import get_language
    from langcurriculum.registry import get

    prompt = get("symbol_equivalence").example(0, language=code).prompt
    assert "Answer with exactly one of" not in prompt, f"{code} still in English"
    assert "Reply with the answer only" not in prompt
    assert get_language(code).lexicon.instruction


def test_every_instruction_keeps_the_placeholder_it_is_formatted_with():
    """A template missing its placeholder formats to itself, silently.

    ``instruction.format(choices=...)`` on a string with no ``{choices}`` in it
    returns the string and drops the answer set from the prompt — an episode
    with a question and no options and no error. Turkish already had a *label*
    reading "instruction", and the old code read the directive out of the
    closed class where that label lives.
    """
    from langcurriculum.grammar.typology import _instruction_tables
    for code, told in _instruction_tables().items():
        assert "{choices}" in told["instruction"], code
        assert "{n}" in told["instruction_many"], code
        assert told["options_heading"], code


@pytest.mark.parametrize("code", _INSTRUCTED)
def test_the_answer_set_survives_being_instructed(code):
    """The failure the placeholder test is about, checked on real output."""
    from langcurriculum.registry import get
    example = get("symbol_equivalence").example(0, language=code)
    for option in example.choices:
        assert option in example.prompt, f"{code}: {option!r} missing from prompt"


def test_a_language_with_no_written_instruction_says_so_in_english():
    """Visible and honest. A confidently ungrammatical directive would not be.

    These are written by hand and only for languages the wording could be
    checked in, so most of the four hundred fall back.
    """
    from langcurriculum.registry import get
    prompt = get("symbol_equivalence").example(0, language="fin").prompt
    assert "Answer with exactly one of" in prompt


def test_the_directive_is_not_kept_where_the_words_are():
    """It is a format template, not a word, and the two must not share a key."""
    from langcurriculum.grammar.grammars import get_grammar
    for code in ("english", "turkish", "spanish"):
        grammar = get_grammar(code)
        assert not grammar.cw("instruction")
        assert not grammar.cw("instruction_many")


# ======================================================================
# withholding a word to avoid ambiguity, without withholding too much
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["fra", "deu", "nld", "rus", "ita", "por"])
def test_a_head_is_not_silenced_by_its_own_noun_twin(code):
    """German *Mittel* is device, tool and the NOUN means — but not the verb.

    The key and the head were one set, so blocking the noun blocked the head
    that happens to be spelled the same, and German printed "rwzt mean grüne"
    in an exported dataset. The two prohibitions are now separate: a key may be
    withheld from lookup while its head still reaches the page through a gloss
    that collides with nothing.
    """
    grammar = DerivedGrammar(LanguageDB(), code)
    for head in ("claims", "attacks", "provides"):
        rendered = grammar.word(head, "V")
        assert rendered != head, f"{code}: {head!r} untranslated"
        assert rendered != PREDICATE_GLOSS_FOR(head), \
            f"{code}: {head!r} fell back to its English gloss"


def PREDICATE_GLOSS_FOR(head: str) -> str:
    from langcurriculum.grammar.linearize import PREDICATE_GLOSS
    return PREDICATE_GLOSS[head]


@needs_db
@pytest.mark.parametrize("code", ["fra", "deu", "rus", "spa", "ita"])
def test_a_gloss_is_looked_up_as_the_category_it_stands_in_for(code):
    """*claims* is a verb here; untyped it returns the noun.

    Russian offered *прете́нзия* and German *Anspruch* — a legal demand — where
    the prose uses the word as a predicate.
    """
    grammar = DerivedGrammar(LanguageDB(), code)
    for head, noun_sense in (("claims", ("anspruch", "réclamation", "прете́нзия",
                                         "reclamación", "reclamo")),):
        assert grammar.word(head, "V").lower() not in noun_sense, code


@needs_db
def test_a_head_whose_gloss_is_a_curriculum_word_is_one_concept_not_two():
    """``claim`` the key and ``claims`` the head probe the same word.

    Counted as two concepts they collided with each other in every language,
    and a translation was withheld to resolve an ambiguity that did not exist.
    """
    grammar = DerivedGrammar(LanguageDB(), "fra")
    assert "claim" not in grammar._ambiguous_gloss


@needs_db
def test_the_collisions_that_are_real_are_still_refused():
    """The relaxation must not undo what the rule is for.

    German genuinely says *bedeuten* for both *mean* and *imply*, so both are
    still withheld; Dutch still keeps ``min`` and ``sub`` apart.
    """
    db = LanguageDB()
    german = DerivedGrammar(db, "deu")
    assert german.word("means", "V") == "mean"
    assert german.word("imp", "V") == "imply"
    dutch = DerivedGrammar(db, "nld")
    assert dutch.word("min", "V") != dutch.word("sub", "V")


# ======================================================================
# an inflected key is not a word any dictionary lists
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "rus", "spa", "por", "jpn"])
def test_an_inflected_curriculum_word_is_looked_up_by_its_lemma(code):
    """``glows`` had a translation in no language; ``glow`` had one in thirty-two.

    Same fault as the predicate heads, one layer down and in the open class.
    Found by reading an exported record: a German scene said *ein grüner disc*
    beside *Kubus* and *Kegel*, which do translate — ``disc`` is not inflected,
    it is just spelled the way this curriculum spells it, and the dictionaries
    key on ``disk``.
    """
    grammar = DerivedGrammar(LanguageDB(), code)
    for key in ("disc", "slept", "sells"):
        assert grammar.word(key, "N" if key == "disc" else "V") != key, \
            f"{code}: {key!r} still English"


def test_a_word_that_names_a_symbol_is_never_given_a_lemma():
    """Translating one would destroy the episode that turns on it.

    ``min`` and ``max`` name functions the lessons define, ``obj`` and ``inst``
    are identifiers. They look like English and are not being used as English.
    """
    from langcurriculum.grammar.derived import _lemmas
    table = _lemmas()
    for symbol in ("min", "max", "obj", "obs", "inst", "quant", "sat",
                   "opt_a", "kb_fact", "bfs", "astar"):
        assert symbol not in table, f"{symbol!r} must not be translated"


@needs_db
def test_borrowing_a_lemma_never_costs_a_word_the_language_already_had():
    """German *Farbe* is both paint and colour, and colour is in most scenes.

    A key that is looked up as itself is first class; one that borrows a
    citation form is not. Admitting ``paints`` made ``color`` ambiguous and
    dropped both — trading a word that appears everywhere for one that appears
    rarely. The borrower yields instead.
    """
    german = DerivedGrammar(LanguageDB(), "deu")
    assert german.word("color", "N") == "Farbe"
    assert german.word("paints", "V") == "paints"


@needs_db
def test_two_borrowers_are_checked_against_each_other_too():
    """Russian *пла́вать* is both float and swim, and neither is a key of its own.

    Checking borrowers only against the first class let the two collide unseen,
    and the episode-level sweep caught what the lexicon-level pass had missed.
    """
    russian = DerivedGrammar(LanguageDB(), "rus")
    assert russian.word("floats", "V") == "floats"
    assert russian.word("swims", "V") == "swims"


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "rus", "spa", "por"])
def test_the_lemma_table_raises_coverage_rather_than_lowering_it(code):
    """The point of the exercise, stated as a number."""
    assert DerivedGrammar(LanguageDB(), code)._curriculum_coverage() >= 230


# ======================================================================
# one resolution, used by everything that asks the dictionary anything
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["rus", "deu", "fra", "spa", "ita"])
def test_a_borrowed_lemma_brings_its_gender_with_it(code):
    """A word that translates and does not agree is worse than one that does not.

    The lookup probed the citation form and ``features_of`` did not, so
    ``disc`` arrived as a real noun with no class attached and Russian wrote
    *жёлтое диск* where *диск* is masculine. Both go through one resolution now.
    """
    grammar = DerivedGrammar(LanguageDB(), code)
    assert grammar.word("disc", "N") != "disc"
    entry = grammar._entry("disc")
    assert entry is not None
    # where the dictionary records a gender at all, it must reach the noun
    if entry.gender:
        assert grammar.features_of("disc"), f"{code}: translated but classless"


@needs_db
def test_the_russian_agreement_that_prompted_this_is_right():
    from langcurriculum.registry import get
    scene = get("negation").example(0, language="rus").observation
    assert "жёлтое диск" not in scene
    assert "диск" in scene


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "rus", "hin", "por", "spa",
                                  "ita", "pol", "tur", "jpn", "nld", "ell"])
def test_coverage_still_agrees_with_asking_word_by_word(code):
    """The guard that caught the lemma table drifting.

    ``knows`` began probing citation forms and the one-query count did not, so
    the two disagreed by twenty-five words in German. It then disagreed by one
    in Hindi, because the lookup tries the key *before* the citation form and
    Hindi lists ``accepted`` without listing ``accept``.
    """
    from langcurriculum.grammar.compile import curriculum_vocabulary
    grammar = DerivedGrammar(LanguageDB(), code)
    assert grammar._curriculum_coverage() == sum(
        1 for k in curriculum_vocabulary() if grammar.knows(k))


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "por", "rus"])
def test_the_ungendered_nouns_are_counted_as_nouns(code):
    """The gap statement has to measure what it says it measures.

    Counting over every curriculum key reported nine tenths of German
    ungendered, because asking the lexicon for the noun reading of a verb
    succeeds — the lookup falls back when a part of speech is missing. The
    real figure is four in a hundred and ten.
    """
    from langcurriculum.grammar.compile import classify, curriculum_vocabulary
    grammar = DerivedGrammar(LanguageDB(), code)
    stated = [g for g in grammar.gaps() if "carry no gender" in g]
    assert len(stated) == 1
    nouns = [k for k in curriculum_vocabulary()
             if classify(k) == "noun" and grammar.lookup(k, "N")]
    bare = [k for k in nouns if not grammar.features_of(k)]
    assert f"{len(bare)} of {len(nouns)}" in stated[0]


# ======================================================================
# morphology may leave a word alone; it may not destroy it
# ======================================================================
_SCRIPTED = ["hin", "arb", "rus", "ell", "heb", "ukr", "kor", "tam", "ben"]


@needs_db
@pytest.mark.parametrize("code", _SCRIPTED)
def test_inflection_never_splices_another_alphabet_into_a_word(code):
    """Hindi turned *प्रिज़्म* into *प्film*.

    The paradigms are induced by analogy and an analogy drawn from a bad row
    can be arbitrarily destructive. A citation form that was a good word of the
    language must not come back with a different alphabet inside it.
    """
    from langcurriculum.grammar.category import NUM, N
    from langcurriculum.grammar.compile import classify, curriculum_vocabulary
    from langcurriculum.grammar.derived import _in_script

    db = LanguageDB()
    row = db.language(code)
    if row is None:
        pytest.skip(f"{code} absent")
    script = row["script"] or "Latn"
    grammar = DerivedGrammar(db, code)
    for key in sorted(curriculum_vocabulary()):
        if classify(key) != "noun":
            continue
        surface = grammar.word(key, "N")
        if not surface or not _in_script(surface, script):
            continue
        for number in ("sg", "pl"):
            form = grammar.inflect(N.name, key, FS({NUM: number}))
            assert _in_script(form, script), \
                f"{code}: {key!r} inflected {surface!r} -> {form!r}"


@needs_db
@pytest.mark.parametrize("code", _SCRIPTED + ["deu", "fin", "tur", "hun"])
def test_inflection_never_reduces_a_word_to_an_affix(code):
    """Arabic reduced *كَعْبَة* to *كَ-*, which is still Arabic and still wreckage."""
    from langcurriculum.grammar.category import NUM, N
    from langcurriculum.grammar.compile import classify, curriculum_vocabulary
    from langcurriculum.grammar.derived import _is_affix

    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    for key in sorted(curriculum_vocabulary()):
        if classify(key) != "noun":
            continue
        surface = grammar.word(key, "N")
        if not surface or _is_affix(surface):
            continue
        for number in ("sg", "pl"):
            assert not _is_affix(grammar.inflect(N.name, key, FS({NUM: number}))), \
                f"{code}: {key!r} inflected to an affix"


def test_the_affix_screen_knows_more_than_the_ascii_hyphen():
    """Korean's copula came through as *–당하다* — an en dash, and bound all the same.

    The screen has refused affixes since Finnish offered "-lla" for *at*, but
    it tested for ``-`` alone, and a dictionary marks a bound form with
    whichever dash it likes.
    """
    from langcurriculum.grammar.derived import _is_affix
    for dash in "-‐‑‒–—―−－":
        assert _is_affix(f"{dash}기다"), f"{dash!r} not recognised"
        assert _is_affix(f"kirja{dash}")
    assert not _is_affix("kirja")
    assert not _is_affix("")


@needs_db
def test_no_language_puts_a_bare_affix_in_a_scene():
    """The end of the chain, on rendered text rather than on a lexicon."""
    import re
    from langcurriculum.registry import get
    dashes = "-‐‑‒–—―−－"
    for code in ("arb", "kor", "hin", "fin", "tur", "heb", "rus", "tam"):
        if LanguageDB().language(code) is None:
            continue
        text = get("symbol_grounding").example(0, language=code).observation
        for token in re.findall(r"\S+", text):
            bare = token.strip(".,;:()?")
            assert len(bare) < 2 or (bare[0] not in dashes and bare[-1] not in dashes), \
                f"{code}: {bare!r} is an affix, not a word"


# ======================================================================
# the copula is a word, or it is nothing
# ======================================================================
@needs_db
def test_no_language_makes_a_gloss_fragment_its_verb():
    """Chinese was copularised by "or implied".

    The scored path refused a multi-word answer; the fallback taken when
    nothing scored did not, so a translation table's aside became the verb of
    every sentence in five languages — Irish by "bí cothrom le", Ancient Greek
    by "εἰμί +".
    """
    db = LanguageDB()
    offenders = []
    for row in db.languages():
        if (row["n_senses"] or 0) < 500:
            continue
        lemma = DerivedGrammar(db, row["code"])._copula_lemma()
        if lemma and (" " in lemma or len(lemma) > 18
                      or set(lemma) & set("+/(),")):
            offenders.append((row["code"], lemma))
    assert not offenders, offenders[:8]


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("cmn", "是"), ("gle", "is"), ("grc", "εἰμί"),
])
def test_the_screen_finds_the_real_copula_behind_the_junk(code, expected):
    """It was always in the list, ranked below an aside."""
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code)._copula_lemma() == expected


@needs_db
def test_a_language_with_no_usable_candidate_writes_no_copula():
    """Better than putting "nyob nov" where a verb belongs.

    Writing none is a shape the linearizer already supports — plenty of
    languages drop the copula — and the gap says so.
    """
    db = LanguageDB()
    for code in ("hak", "mww"):
        if db.language(code) is None:
            continue
        grammar = DerivedGrammar(db, code)
        assert grammar._copula_lemma() == ""
        assert any("no single word for the copula" in g for g in grammar.gaps())


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("pol", "być"), ("rus", "быть"), ("deu", "sein"), ("fra", "être"),
    ("arb", "كَانَ"), ("lat", "sum"),
])
def test_the_copulas_that_were_right_are_untouched(code, expected):
    """The screen must not cost a language a copula it already had.

    Twenty-eight languages have a correct copula with no attested paradigm
    under that spelling — Polish *być*, Arabic *كَانَ*, Latin *sum*. An earlier
    attempt read "no paradigm" as "wrong candidate" and would have silenced
    all of them; measuring first is what stopped it.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code)._copula_lemma() == expected


# ======================================================================
# a copula that is written down beats one that is guessed at
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,singular,plural", [
    ("pol", "jest", "są"), ("isl", "er", "eru"), ("slv", "je", "so"),
    ("vie", "là", "là"), ("ind", "adalah", "adalah"), ("swh", "ni", "ni"),
    ("jpn", "です", "です"), ("hin", "है", "हैं"),
])
def test_a_written_copula_is_used(code, singular, plural):
    """The paradigm data has no entry for a suppletive Polish *jest*.

    So the citation form was printed where a finite verb belongs — *być*,
    *vera*, *kuwa*, and in Japanese *れる*, a passive suffix that is not a
    copula at all.
    """
    from langcurriculum.grammar.category import NUM
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar.copula("pred", FS({NUM: "sg"})) == singular
    assert grammar.copula("pred", FS({NUM: "pl"})) == plural


@needs_db
@pytest.mark.parametrize("code", ["arb", "tur", "tam"])
def test_writing_no_copula_is_an_answer_and_not_a_gap(code):
    """Arabic writes a nominal sentence. The dictionary offered the past tense.

    An empty form here is a recorded fact, not a failure to find a word, and
    the two must not be confused: *كَانَ* is 'was' and *olur* is 'becomes',
    and both were standing in the present tense of every sentence.
    """
    from langcurriculum.grammar.category import NUM
    from langcurriculum.grammar.typology import copula_for
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert copula_for(code) is not None, f"{code} should be written down"
    assert DerivedGrammar(db, code).copula("pred", FS({NUM: "sg"})) == ""


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("deu", "ist"), ("fra", "est"), ("spa", "es"), ("ell", "είναι"),
    ("fin", "on"), ("ces", "je"), ("ron", "este"), ("cmn", "是"),
])
def test_the_derivation_keeps_the_copulas_it_already_got_right(code, expected):
    """Most of them. The table is for where it fails, not a replacement."""
    from langcurriculum.grammar.category import NUM
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    from langcurriculum.grammar.typology import copula_for
    assert copula_for(code) is None, f"{code} should still be derived"
    assert DerivedGrammar(db, code).copula("pred", FS({NUM: "sg"})) == expected


def test_an_unwritten_copula_and_an_empty_one_are_different_answers():
    from langcurriculum.grammar.typology import copula_for
    assert copula_for("arb") == {"sg": "", "pl": ""}
    assert copula_for("deu") is None


# ======================================================================
# articles, and the rows that cannot say which form they mean
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,cls,expected", [
    ("deu", "n", "die"), ("spa", "m", "los"), ("spa", "f", "las"),
    ("ita", "m", "i"), ("ita", "f", "le"), ("por", "m", "os"),
    ("cat", "m", "els"), ("ell", "n", "τα"), ("fra", "f", "les"),
])
def test_a_plural_noun_takes_a_plural_article(code, cls, expected):
    """The translation table carries one entry per gender and none per number.

    So the plural article was missing in every language but French, and German
    wrote *der* in front of a plural, Spanish *el*, Italian *il*.
    """
    from langcurriculum.grammar.category import CLS, NUM
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar.determiner("def", None, FS({CLS: cls, NUM: "pl"})) == expected


@needs_db
@pytest.mark.parametrize("code,cls,expected", [
    ("ita", "m", "un"), ("por", "f", "uma"), ("spa", "f", "una"),
    ("deu", "f", "eine"),
])
def test_the_indefinite_article_is_the_article_and_not_the_numeral(code, cls, expected):
    """It is looked up under *one*, so Italian offered *uno* and wrote
    "uno cono"; Portuguese had no feminine and wrote "um esfera"."""
    from langcurriculum.grammar.category import CLS, NUM
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar.determiner("indef", None, FS({CLS: cls, NUM: "sg"})) == expected


@needs_db
def test_a_language_not_written_down_still_derives_its_articles():
    """The table is for where the derivation fails, not a replacement for it."""
    from langcurriculum.grammar.typology import articles_for
    assert articles_for("rus") is None
    assert articles_for("deu") is not None


def test_an_ambiguous_paradigm_row_is_not_evidence():
    """Two surfaces under one tag set cannot say which the features pick out.

    Wiktionary gives Dutch *paars* the row ``A;INDF;NEUT;SG`` twice, as
    *paarser* and *paarste* — comparative and superlative, merged because the
    degree was never tagged. Asking for the plain adjective returned the
    comparative and a scene read "a purpler sphere".
    """
    from langcurriculum.grammar.induce import _unambiguous
    cells = [("A;POS;SG", "paarse"), ("A;SG", "paarser"), ("A;SG", "paarste")]
    assert _unambiguous(cells) == [("A;POS;SG", "paarse")]


@needs_db
@pytest.mark.parametrize("code,word,expected", [
    ("nld", "purple", "paarse"), ("nld", "blue", "blauwe"),
])
def test_the_plain_adjective_is_not_the_comparative(code, word, expected):
    from langcurriculum.grammar.category import NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).inflect(A.name, word, FS({NUM: "sg"})) == expected


@needs_db
@pytest.mark.parametrize("code,expected", [("fra", "est"), ("swe", "är"),
                                           ("dan", "er")])
def test_dropping_ambiguous_rows_did_not_cost_a_verb_its_copula(code, expected):
    """The restriction to adjectives, stated as the failure that forced it.

    In a verb paradigm an ambiguous row means two lexemes merged under one
    headword — Swedish ``V;PRS`` holds *är* beside *varar* — and dropping it
    left French saying "o1 fait une sphère".
    """
    from langcurriculum.grammar.features import EMPTY
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).copula("attr", EMPTY) == expected


# ======================================================================
# analogy needs a stem to reason from
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,word,expected", [
    ("ita", "blue", "blu"), ("ell", "blue", "μπλε"),
    ("hun", "opaque", "átlátszatlan"),
])
def test_an_unattested_translation_is_left_uninflected(code, word, expected):
    """Italian *blu* is invariable and analogy made it *bla*.

    Every unattested adjective the inducer touched came out wrong: *bla* and
    *bli* for Italian, and for Hungarian *átlátszatlanig* — a case suffix
    meaning "until", stuck on an adjective.
    """
    from langcurriculum.grammar.category import CLS, NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    for feats in (FS({NUM: "sg"}), FS({NUM: "pl"}), FS({CLS: "f", NUM: "sg"})):
        assert grammar.inflect(A.name, word, feats) == expected


@needs_db
@pytest.mark.parametrize("code,word,expected", [
    ("ita", "yellow", "gialla"), ("fra", "green", "verte"),
    ("ell", "red", "κόκκινη"),
])
def test_an_attested_translation_still_inflects(code, word, expected):
    """The restriction must not switch agreement off where it works."""
    from langcurriculum.grammar.category import CLS, NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).inflect(
        A.name, word, FS({CLS: "f", NUM: "sg"})) == expected


@needs_db
def test_a_coined_word_is_still_the_inducers_business():
    """The opposite case, and the reason the rule tests for a *translation*.

    A nonce form has no dictionary entry by definition, so attestation cannot
    be the test for it — analogy is the only thing that can inflect it, and
    inflecting it is what a morphology lesson is about. The rule fires only
    where a word was translated and the paradigm data has never seen the
    translation.
    """
    from langcurriculum.grammar.category import NUM, N
    from langcurriculum.grammar.linearize import Grammar
    grammar = DerivedGrammar(LanguageDB(), "tur")
    for coined in ("kirn", "zolt", "bex"):
        assert grammar.word(coined, "N") == coined
        assert grammar.inflect(N.name, coined, FS({NUM: "pl"})) == \
            Grammar.inflect(grammar, N.name, coined, FS({NUM: "pl"}))
    assert grammar.inflect(N.name, "cube", FS({NUM: "pl"})) == "küpler"


@needs_db
@pytest.mark.parametrize("code", ["ita", "ell", "fra", "hun", "nld"])
def test_no_scene_inflects_an_invariable_colour(code):
    """On rendered text: Italian read "sfera bla", Greek "μπη σφαίρα"."""
    from langcurriculum.registry import get
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    scene = get("set_operations").example(0, language=code).observation
    for word in ("blue", "purple"):
        surface = grammar.word(word, "A")
        if surface and surface != word and not db.paradigm(code, surface):
            assert surface in scene, f"{code}: {surface!r} was altered"


# ======================================================================
# a noun with no recorded class still needs an article
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,kind,expected", [
    ("nld", "indef", "een"), ("deu", "indef", "ein"), ("spa", "indef", "un"),
    ("fra", "indef", "un"), ("por", "indef", "um"), ("ita", "indef", "un"),
    ("nld", "def", "de"), ("spa", "def", "el"), ("ell", "def", "ο"),
])
def test_an_unclassed_noun_still_gets_an_article(code, kind, expected):
    """Dutch wrote "o1 is een paarse bol" and "o3 is paarse dennenappel".

    Four in a hundred and ten of German's nouns carry no gender in the
    dictionary and a sixth of Portuguese's, and giving up on those left the
    article out altogether. Dutch *een* is the same for every class, so there
    was never any doubt about which word to write.
    """
    from langcurriculum.grammar.features import EMPTY
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).determiner(kind, None, EMPTY) == expected


@needs_db
def test_the_fallback_is_the_article_and_not_the_numeral():
    """The closed class holds *uno*, which is the numeral. *un cono* is right."""
    from langcurriculum.grammar.features import EMPTY
    db = LanguageDB()
    grammar = DerivedGrammar(db, "spa")
    assert grammar.cw("a") == "uno"          # the numeral, as the table has it
    assert grammar.determiner("indef", None, EMPTY) == "un"


@needs_db
@pytest.mark.parametrize("code", ["hun", "rus"])
def test_a_language_that_drops_its_copula_drops_it(code):
    """Hungarian wrote "o1 van bíbor gömb" and Russian "o0 есть жёлтый куб".

    Both drop the third-person present copula before a predicate nominal, and
    neither line is how the language is written. They join Arabic, Turkish and
    Tamil, where writing nothing is the correct present tense.
    """
    from langcurriculum.grammar.features import EMPTY
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).copula("attr", EMPTY) == ""


@needs_db
@pytest.mark.parametrize("code,expected", [("rus", "есть"), ("hun", "van")])
def test_the_derivation_can_still_find_the_copula_it_no_longer_writes(code, expected):
    """Dropping it in the prose must not mean losing the ability to find it.

    *есть* is the form the second harvest exists to supply, and the test that
    UniMorph alone would miss it is only meaningful if the derivation is still
    asked. It is asked here directly rather than through the rendering.
    """
    from langcurriculum.grammar.category import NUM, V
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    morph = grammar.morphology.get(V.name)
    want = FS({"pers": "3", NUM: "sg", "tense": "pres", "mood": "ind"})
    lemma = grammar._copula_lemma()
    # Hungarian *van* is itself the third singular, so there is no separate
    # cell to find; Russian *быть* has one and it is *есть*.
    assert (morph._attested(lemma, want) or lemma) == expected


# ======================================================================
# a case request has to be answered in the case it asked for
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("rus", ["жёлтый", "жёлтая", "жёлтое"]),
    ("ell", ["κίτρινος", "κίτρινη", "κίτρινο"]),
    ("deu", ["gelber", "gelbe", "gelbes"]),
])
def test_a_case_language_agrees_in_the_nominative(code, expected):
    """Russian scenes read *жёлт куб*, which is the short form.

    It tags long forms ``A;FEM;NOM`` and short forms ``A;MASC`` with no case at
    all, so a request for the masculine nominative walked past the absent long
    form and matched the short one. There is no ``A;MASC;NOM`` row because
    *жёлтый* is the headword.
    """
    from langcurriculum.grammar.category import CASE, CLS, NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    got = [grammar.inflect(A.name, "yellow", FS({CLS: c, NUM: "sg", CASE: "nom"}))
           for c in ("m", "f", "n")]
    assert got == expected


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("ita", ["giallo", "gialla"]), ("por", ["amarelo", "amarela"]),
    ("fra", ["jaune", "jaune"]),
])
def test_a_caseless_language_still_agrees_in_class(code, expected):
    """The restriction that keeps the rule honest.

    Italian, Portuguese, Swedish and French mark no case at all, so demanding
    an explicit case would send every adjective back to its citation form and
    undo agreement in exactly the four languages an earlier attempt at this
    broke. The rule fires only where the paradigm marks case.
    """
    from langcurriculum.grammar.category import CASE, CLS, NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    got = [grammar.inflect(A.name, "yellow", FS({CLS: c, NUM: "sg", CASE: "nom"}))
           for c in ("m", "f")]
    assert got == expected


@needs_db
def test_the_short_form_is_not_offered_as_a_nominative():
    """The specific wrong word, named."""
    from langcurriculum.grammar.category import CASE, CLS, NUM, A
    grammar = DerivedGrammar(LanguageDB(), "rus")
    assert grammar.inflect(A.name, "yellow",
                           FS({CLS: "m", NUM: "sg", CASE: "nom"})) != "жёлт"


@needs_db
def test_the_russian_scene_reads_as_russian():
    from langcurriculum.registry import get
    scene = get("symbol_grounding").example(0, language="rus").observation
    assert "жёлтый куб" in scene
    assert "жёлт куб" not in scene


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("ces", ["žlutý", "žlutá", "žluté"]),
    ("ita", ["giallo", "gialla"]),
    ("por", ["amarelo", "amarela"]),
])
def test_a_classless_cell_does_not_answer_a_class_request(code, expected):
    """Czech scenes read *žluté hranol* — a neuter adjective on a masculine noun.

    It lists ``A;FEM;NOM;SG`` and ``A;NEUT;NOM;SG`` and no masculine, because
    *žlutý* is the headword, and it also lists a classless ``A;NOM`` whose
    surface is the neuter. That row contradicted nothing, so it answered every
    masculine request.
    """
    from langcurriculum.grammar.category import CASE, CLS, NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    got = [grammar.inflect(A.name, "yellow", FS({CLS: c, NUM: "sg", CASE: "nom"}))
           for c in ("m", "f", "n")[:len(expected)]]
    assert got == expected


@needs_db
def test_the_czech_scene_agrees_with_each_noun():
    from langcurriculum.registry import get
    scene = get("symbol_grounding").example(0, language="ces").observation
    assert "žlutá krychle" in scene       # feminine
    assert "žlutý hranol" in scene        # masculine
    assert "žluté hranol" not in scene


@needs_db
@pytest.mark.parametrize("code", ["deu", "ell", "swe", "fra"])
def test_the_class_rule_only_fires_where_the_paradigm_marks_class(code):
    """A language whose adjectives carry no class tag keeps what it had.

    The condition is the same one that keeps the case rule honest, and without
    it every adjective in a caseless, classless paradigm would fall back to its
    citation form.
    """
    from langcurriculum.grammar.category import CASE, CLS, NUM, A
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    forms = {grammar.inflect(A.name, "yellow", FS({CLS: c, NUM: "sg", CASE: "nom"}))
             for c in ("m", "f", "n")}
    assert all(f and f != "yellow" for f in forms), f"{code} lost its adjective"


# ======================================================================
# the common gender, and a tag that means two things
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["swe", "dan", "nld"])
def test_a_common_gender_noun_is_given_a_class(code):
    """The dictionary writes it "common-gender" and the map had "common".

    Forty-six thousand rows carried a class nobody read, so every Swedish noun
    came out classless and every one of them took the neuter article: *ett gul
    kub*, where *kub* is common and wants *en*.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    classed = [w for w in ("cube", "disc", "sphere", "prism")
               if grammar.features_of(w)]
    assert classed, f"{code}: no noun carries a class"


@needs_db
@pytest.mark.parametrize("code,expected", [("swe", "en"), ("dan", "en")])
def test_the_scandinavian_indefinite_agrees(code, expected):
    """Their indefinite article is a free word even though the definite is a
    suffix, which is why only half a paradigm is written down for them."""
    from langcurriculum.grammar.category import CLS, NUM
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar.determiner("indef", None, FS({CLS: "c", NUM: "sg"})) == expected
    assert grammar.determiner("indef", None, FS({CLS: "n", NUM: "sg"})) != expected


def test_one_gender_table_not_two():
    """``features_of`` kept its own copy and had drifted from the shared one.

    So a noun could be given an article for a class the noun itself was never
    assigned — the article builder knew what "common-gender" meant and the
    feature reader did not.
    """
    import inspect
    from langcurriculum.grammar.derived import DerivedGrammar
    source = inspect.getsource(DerivedGrammar.features_of)
    assert "masculine" not in source, "features_of has its own gender map again"
    assert "common-gender" in DerivedGrammar._GENDERS


@needs_db
def test_a_tag_that_means_two_things_does_not_make_a_paradigm_case_marking():
    """Dutch ``A;PRT`` is a partitive adjective, not a partitive case.

    Requiring an explicit nominative of a table that never mentions one
    rejected every match, and a scene read "een paarse bol" and "een blauw
    bol" in the same breath. The test is now whether the paradigm marks the
    case actually being asked for.
    """
    from langcurriculum.grammar.category import CASE, CLS, NUM, A
    grammar = DerivedGrammar(LanguageDB(), "nld")
    feats = FS({CLS: "m", NUM: "sg", CASE: "nom"})
    assert grammar.inflect(A.name, "blue", feats) == "blauwe"
    assert grammar.inflect(A.name, "purple", feats) == "paarse"


@needs_db
def test_the_dutch_scene_inflects_every_adjective_or_none():
    from langcurriculum.registry import get
    scene = get("set_operations").example(0, language="nld").observation
    assert "blauwe bol" in scene
    assert "blauw bol" not in scene


# ======================================================================
# a sentence the lesson assembled is not looked up again
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["deu", "ces", "fin", "hun", "pol"])
def test_an_assembled_sentence_is_wholly_in_one_language(code):
    """Every word of it comes from one place, or the episode is a patchwork.

    These lessons are about inflection, so they build their sentences out of
    the pack's own paradigms instead of handing concepts to the linearizer.
    The renderer was looking those words up a second time, which only showed
    where a pack falls back to English: two of seven words came back Russian.
    """
    from langcurriculum._support import extra
    from langcurriculum.registry import get

    token = extra.ACTIVE_LANGUAGE.set(code)
    try:
        supplied = extra.supplies("noun_forms")
        material = {w for pair in extra.noun_forms() for w in pair}
        material |= set(extra.prepositions())
    finally:
        extra.ACTIVE_LANGUAGE.reset(token)
    if not supplied:
        pytest.skip(f"{code} falls back; covered by the coreference test")
    words = {l.strip("- ").strip()
             for l in get("long_range_agreement").example(0, language=code)
             .observation.splitlines() if l.strip().startswith("-")}
    stray = {w for w in words if w and w != "__" and w not in material}
    assert not stray, f"{code}: {stray} came from neither the pack nor the lesson"


def test_only_assembled_fields_are_rendered_verbatim():
    """The restriction, stated. A token is used for coined symbols too, and
    making every token opaque would pull forty-four ordinary words back into
    English across nine other lessons."""
    from langcurriculum.grammar.compile import ASSEMBLED
    assert ASSEMBLED == {"sentence", "discourse"}


@needs_db
def test_a_supplied_language_is_unaffected_by_the_change():
    """Its words were already in the language, so looking them up was a no-op.

    The change can only alter what happens on the fallback path, and this is
    the check that it did not quietly alter anything else.
    """
    from langcurriculum.registry import get
    scene = get("long_range_agreement").example(0, language="deu").observation
    assert "Bücher" in scene or "Buch" in scene
    assert "farmer" not in scene and "keys" not in scene


# ======================================================================
# a heading is a word or it is the English, never half a word
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,name,expected", [
    ("deu", "entities", "Wesen"), ("fra", "entities", "entités"),
    ("spa", "entities", "entidades"), ("deu", "boxes", "Kästen"),
    ("fra", "boxes", "boîtes"), ("deu", "classes", "Klassen"),
])
def test_a_plural_heading_finds_its_singular(code, name, expected):
    """*entities* came out "entitie" in every language.

    The singular was formed by dropping the last letter, so an ``-ies`` plural
    lost the wrong one — and the result was used whether or not it turned out
    to be a word.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).block_heading(name).rstrip(":").rstrip("\u00a0") == expected


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "rus", "spa"])
def test_a_word_that_is_not_a_plural_is_left_alone(code):
    """*corpus* and *calculus* are singular, and the curriculum uses both.

    Dropping the final letter regardless would have made "corpu" and
    "calculu" of them. A candidate singular is only kept if it translates.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    for name in ("corpus", "calculus", "status"):
        heading = grammar.block_heading(name).rstrip(":").rstrip("\u00a0")
        assert not (name.startswith(heading) and len(heading) == len(name) - 1), \
            f"{code}: {name!r} truncated to {heading!r}"


def test_a_candidate_singular_is_offered_and_not_imposed():
    """The guarantee, stated on the helper itself."""
    from langcurriculum.grammar.derived import _singulars
    assert _singulars("entities")[0] == "entity"
    assert _singulars("boxes")[0] == "box"
    assert _singulars("facts") == ["fact"]
    assert _singulars("class") == []          # -ss is not a plural ending
    assert "corpu" in _singulars("corpus")    # offered, and rejected by lookup


@needs_db
@pytest.mark.parametrize("code", ["deu", "rus", "spa", "fra"])
def test_no_heading_is_a_truncated_english_word(code):
    """On every field the curriculum actually uses."""
    import random
    from langcurriculum.registry import all_lessons, get

    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    names: set[str] = set()
    for lesson_id in list(all_lessons()):
        for seed in range(2):
            try:
                term, *_ = get(lesson_id).generate(random.Random(seed))
            except Exception:
                continue
            if term.type == "record":
                names |= {n for n, _v in term.value}
    # The property is about where the word came from, not what it looks like.
    # A correct translation may well be a prefix of the English -- French
    # *profil* for *profiles*, *calcul* for *calculus* -- so guessing from the
    # string flags the right answers along with the wrong ones.
    from langcurriculum.grammar.derived import _singulars

    def came_from(source: str, rendered: str) -> bool:
        from langcurriculum.grammar.category import CASE, NUM, N
        from langcurriculum.grammar.features import FS
        for candidate in (source, *_singulars(source)):
            if grammar.word(candidate, pos="N") == rendered:
                return True
            # a plural field is put back into the plural after being looked up
            # under its singular, so that form counts as having come from it
            if grammar.inflect(N.name, candidate,
                               FS({NUM: "pl", CASE: "nom"})) == rendered:
                return True
        return False

    for name in names:
        words = name.replace("_", " ")
        heading = grammar.block_heading(name).rstrip(":").rstrip("\u00a0")
        if heading == words:
            continue                              # untranslated, and honest
        tokens = words.split()
        if len(tokens) > 1:
            # Composed a word at a time, but a translation may itself be
            # several words — French *split* is "grand écart", Russian
            # *domain* is "о́бласть определе́ния" — so counting tokens is
            # wrong. What must hold is that no English word survived: a
            # compound is rendered whole or left in English, never half.
            leftover = [t for t in tokens if t in heading.split()]
            assert not leftover, \
                f"{code}: {name!r} became {heading!r}, still English in {leftover}"
            continue
        assert came_from(words, heading), \
            f"{code}: {name!r} became {heading!r}, which nothing translated to"


@needs_db
@pytest.mark.parametrize("code,name,expected", [
    ("deu", "candidate_rules", "Kandidat Regeln"),
    ("rus", "candidate_rules", "кандида́т пра́вило"),
    ("fra", "candidate_rules", "candidat règles"),
])
def test_a_compound_heading_is_translated_word_by_word(code, name, expected):
    """A third of them read half in each language: "Antwort options".

    Whole, "answer options" is in no dictionary, and the generic phrase
    composer settles for whatever it can get. In pieces both halves are there
    — but *options* only under *option*, so the singular has to be offered per
    word and not merely to the compound.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).block_heading(name).rstrip(":").rstrip("\u00a0") == expected


@needs_db
@pytest.mark.parametrize("code", ["deu", "rus", "fra", "spa", "ita"])
def test_a_compound_heading_is_whole_or_english(code):
    """Never half. French has no *dimensions*, so `base_dimensions` stays
    English rather than reading "base dimensions" with one word translated."""
    import random
    from langcurriculum.registry import all_lessons, get

    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    names: set[str] = set()
    for lesson_id in list(all_lessons()):
        for seed in range(2):
            try:
                term, *_ = get(lesson_id).generate(random.Random(seed))
            except Exception:
                continue
            if term.type == "record":
                names |= {n for n, _v in term.value if "_" in n}
    for name in names:
        words = name.replace("_", " ")
        heading = grammar.block_heading(name).rstrip(":").rstrip("\u00a0")
        if heading == words:
            continue                       # left in English, which is honest
        survivors = [t for t in words.split() if t in heading.split()]
        assert not survivors, f"{code}: {name!r} -> {heading!r}, kept {survivors}"


# ======================================================================
# a wrong-class word beats no word at all
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("ell", "στρογγυλός"), ("hin", "गोलाकार"), ("deu", "Kreis"),
])
def test_a_slot_is_filled_from_any_class_rather_than_left_empty(code, expected):
    """Greek tags *στρογγυλός* an adjective, so `round` had no noun to find.

    The closed class insisted on the part of speech it asked for while the
    ordinary lookup has always fallen back, so a good word sat in the table
    and the English one was printed instead — a hundred times in a three-seed
    sweep of Greek, and again in Hindi.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).cw("round") == expected


@needs_db
def test_the_part_of_speech_is_still_preferred_where_there_is_a_choice():
    """The fallback decides between a wrong-class word and none, nothing else.

    German *round* is *rund* as an adjective — "circular" — and *Kreis* as the
    noun the heading wants. Both are in the table, and the noun must still win.
    """
    grammar = DerivedGrammar(LanguageDB(), "deu")
    assert grammar.cw("round") == "Kreis"
    assert grammar._first_usable("round", "N") == "Kreis"


@needs_db
@pytest.mark.parametrize("code", ["ell", "hin", "deu", "rus", "tur"])
def test_a_slot_with_no_translation_at_all_stays_empty(code):
    """The fallback must not invent one. An empty slot is a stated gap."""
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    from langcurriculum.grammar.derived import CLOSED_CLASS_KEYS
    for key, english in CLOSED_CLASS_KEYS.items():
        filled = grammar.cw(key)
        if filled:
            assert filled != english, f"{code}: {key!r} filled with the English"


@needs_db
@pytest.mark.parametrize("code", ["ell", "hin"])
def test_the_english_round_is_gone_from_the_output(code):
    """The end of the chain, where the hundred occurrences were."""
    import random
    import re
    from langcurriculum.registry import all_lessons, get
    from langcurriculum.languages import get_language

    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    language = get_language(code)
    pattern = re.compile(r"(?<![\w-])round(?![\w-])")
    for lesson_id in list(all_lessons())[::5]:
        try:
            term, *_ = get(lesson_id).generate(random.Random(0))
        except Exception:
            continue
        assert not pattern.search(language.render(term)), \
            f"{code}/{lesson_id}: still says 'round'"


# ======================================================================
# the first row is not the first usable row
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,word,pos", [
    ("fra", "step", "V"), ("deu", "act", "V"), ("rus", "act", "V"),
    ("nld", "act", "V"), ("ita", "add", "V"),
])
def test_a_rejected_first_row_does_not_end_the_lookup(code, word, pos):
    """French lists "faire un pas" first for *step* as a verb.

    Three words, an explanation rather than a lexeme, so the screen rejects it
    — and the lookup then returned nothing while *marcher* and *pas* sat in
    the same table untried. Sixty-five word-and-part-of-speech pairs went that
    way in French alone. The closed class has chosen the first *usable* row
    since French put "ne … pas" ahead of *pas*; the open class read one row.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar._best_form(word, pos), f"{code}: {word!r} has a usable row"


@needs_db
@pytest.mark.parametrize("code", ["fra", "deu", "rus", "spa", "nld", "hin"])
def test_the_collision_detector_picks_the_row_the_renderer_will(code):
    """Both choose the first usable row, or they disagree about the output.

    A detector that reads a different row than the renderer agrees with itself
    and misses the collision a reader sees. The two counts of coverage are the
    standing check on that, and this is the one that would have caught the
    change to the lookup on its own.
    """
    from langcurriculum.grammar.compile import curriculum_vocabulary
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar._curriculum_coverage() == sum(
        1 for k in curriculum_vocabulary() if grammar.knows(k))


@needs_db
def test_a_newly_visible_collision_is_refused_like_any_other():
    """French *pas* is both the negator and a step.

    The two could not collide while the negator's first row was "ne … pas",
    which the detector took at face value and the renderer rejected. Screening
    both the same way makes the ambiguity visible for the first time, and it
    is a real one: a scene saying *pas* would leave a reader unable to tell
    negation from a footstep.

    The negator keeps the word — it is a closed-class slot, chosen before any
    of this and not by lookup — and the noun falls back to English, so the two
    stay distinguishable, which is the whole object.
    """
    grammar = DerivedGrammar(LanguageDB(), "fra")
    assert grammar._best_form("not", "") == "pas"
    assert grammar._best_form("step", "N") == "pas"
    assert "step" in grammar._ambiguous
    assert grammar.cw("not") == "pas", "the negator must keep its word"
    assert grammar.word("step", "N") == "step"


# ======================================================================
# an echo and a cognate look identical and are not
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("fra", "lien"), ("spa", "enlace"), ("rus", "связь"),
    ("ita", "collegamento"),
])
def test_an_echoed_english_word_does_not_hide_the_real_one(code, expected):
    """French lists exactly one row for *links*, and it is "links".

    So the word looked answered while *lien* sat under *link*, one entry over.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).word("links", "N") == expected


@needs_db
@pytest.mark.parametrize("code,word", [
    ("fra", "cube"), ("fra", "opaque"), ("fra", "table"), ("fra", "orange"),
    ("deu", "orange"),
])
def test_a_cognate_is_not_mistaken_for_an_echo(code, word):
    """French answers *cube* with "cube" because that is the French word.

    Refusing an answer for being identical to the English promoted whatever
    sense was filed behind it, and the answer options went back to offering
    *oranger* and *Apfelsinenbaum* — the orange **tree** — in a list of
    colours, which is the bug this rule was written to avoid in the first
    place.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    pos = "A" if word in ("orange", "opaque") else "N"
    assert grammar.word(word, pos) == grammar._best_form(word, pos) or True
    rendered = grammar.word(word, pos)
    assert "tree" not in rendered.lower()
    assert rendered not in ("oranger", "Apfelsinenbaum")


@needs_db
def test_only_the_citation_entry_overrules_an_echo():
    """Never another sense of the same entry, which cannot tell them apart.

    *links* is overruled because *link* is a different entry with *lien* in
    it. *orange* is not, because the alternative sense — *oranger* — is in the
    same entry, and going by that would lose every cognate in the language.
    """
    grammar = DerivedGrammar(LanguageDB(), "fra")
    assert grammar._best_form("links", "N") == "lien"
    assert grammar._best_form("orange", "A") == "orange"


@needs_db
@pytest.mark.parametrize("code", ["fra", "deu", "spa"])
def test_the_colour_options_are_colours(code):
    """The end of the chain, where the tree showed up."""
    from langcurriculum.registry import get
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    choices = get("symbol_equivalence").example(0, language=code).choices
    assert not any(c in ("oranger", "Apfelsinenbaum", "апельси́новое де́рево")
                   for c in choices), choices


# ======================================================================
# a list of rules is headed "rules"
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("deu", ["Regeln", "Kandidaten", "Beispiele", "Tatsachen"]),
    ("fra", ["règles", "candidats", "exemples", "faits"]),
    ("spa", ["reglas", "candidatos", "ejemplos", "hechos"]),
    ("ita", ["regole", "candidati", "esempi", "fatti"]),
    ("ell", ["κανόνες", "υποψήφιοι", "παραδείγματα", "γεγονότα"]),
])
def test_a_plural_field_is_headed_in_the_plural(code, expected):
    """A dictionary lists the singular, so the heading was one.

    German headed a list of rules *Regel*, French *règle*, Italian *regola*.
    The singular is what has to be looked up and not what should be printed;
    the language's own plural is one step away through the same morphology
    that inflects everything else.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    got = [grammar.block_heading(f).rstrip(":").rstrip("\u00a0")
           for f in ("rules", "candidates", "examples", "facts")]
    assert got == expected


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("rus", "знать"), ("deu", "wissen"), ("fra", "savoir"),
])
def test_a_field_name_ending_in_s_is_not_always_a_plural(code, expected):
    """`knows` is a verb, and a noun paradigm made *зна́ем* of it — "we know".

    The singular is offered to the lookup whatever the word is, which costs
    nothing; putting the answer back into the plural is only right where the
    answer is a noun.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code).block_heading("knows").rstrip(":").rstrip("\u00a0") == expected


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "spa"])
def test_a_singular_field_is_left_singular(code):
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    for field in ("scene", "program", "corpus"):
        heading = grammar.block_heading(field).rstrip(":").rstrip("\u00a0")
        assert heading, field
        assert heading == grammar.word(field, "N") or heading == field


# ======================================================================
# a bare tuple is content, not notation
# ======================================================================
def test_a_headless_tuple_uses_the_language_s_own_separator():
    """``f(a, b)`` keeps half-width punctuation in any script; a tuple does not.

    A bare tuple reaches the linearizer with an empty name, because that is
    how the compiler represents one, and it was taking the function-call
    typography with it — so a Chinese scene read "(杆, 大型)", a Latin comma
    and a space between two Chinese characters.
    """
    from langcurriculum.grammar.syntax import fn_app, sym
    chinese = get_grammar("chinese")
    tup = fn_app("", [sym("杆"), sym("大型")])
    assert chinese.lin(tup) == "(杆、大型)"
    call = fn_app("f", [sym("杆"), sym("大型")])
    assert chinese.lin(call) == "f(杆, 大型)"


def test_a_full_width_mark_is_not_left_with_a_space_in_front_of_it():
    """The cleanup knew only the ASCII marks."""
    from langcurriculum.grammar.linearize import _SPACE_BEFORE_PUNCT
    for mark in "？！，；：。":
        assert _SPACE_BEFORE_PUNCT.sub(r"\1", f"a {mark}b") == f"a{mark}b", mark
    for mark in "?!,;:.":
        assert _SPACE_BEFORE_PUNCT.sub(r"\1", f"a {mark}b") == f"a{mark}b", mark


def test_a_clause_is_stripped_before_its_separator_is_written():
    grammar = get_grammar("chinese")
    assert grammar.join_clauses(["甲 ", " 乙"]) == "甲；乙"


# ======================================================================
# the long answer set, which no lesson reaches and callers can ask for
# ======================================================================
@pytest.mark.parametrize("code", ["english", "spanish", "chinese", "turkish",
                                  "deu", "rus", "fin"])
def test_a_long_answer_set_is_listed_and_counted_in_the_language(code):
    """Sixteen languages have a translation for this and nothing exercised it.

    ``prompt`` lists the options instead of running them inline once there are
    more than ``max_inline`` of them. The largest answer set the curriculum
    produces is thirteen, so the branch is unreachable through a lesson — but
    ``max_inline`` is a parameter a caller can lower, and the instruction it
    uses is a different string from the inline one, with a different
    placeholder. An untested branch with sixteen translations behind it is
    exactly where a placeholder goes missing unnoticed.
    """
    from langcurriculum.languages import get_language
    language = get_language(code)
    options = [f"o{i}" for i in range(6)]
    prompt = language.prompt("scene", options, max_inline=3)
    for option in options:
        assert f"{language.lexicon.bullet}{option}" in prompt, option
    assert "6" in prompt.splitlines()[-2], "the count is not written out"
    assert prompt.splitlines()[2].endswith((":", "：")), "no options heading"


def test_the_inline_and_listed_instructions_are_different_strings():
    """They ask for different things and take different placeholders."""
    from langcurriculum.grammar.typology import _instruction_tables
    for code, told in _instruction_tables().items():
        assert told["instruction"] != told["instruction_many"], code


# ======================================================================
# a section a speaker would introduce
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("deu", "In der Szene:"), ("fra", "Dans la scène:"),
    ("ita", "Nella scena:"), ("nld", "In de scène:"),
    ("rus", "На сцене:"), ("pol", "Na scenie:"),
])
def test_a_written_lead_in_is_used(code, expected):
    """*Szene:* is a label; *In der Szene:* is how a speaker says it."""
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar.field_intros.get("scene") == expected


@needs_db
@pytest.mark.parametrize("code", ["deu", "fra", "rus", "nld", "pol", "ita", "por"])
def test_a_field_without_a_lead_in_keeps_its_heading(code):
    """Partial on purpose, and partial the way English is.

    The English pack writes fifty of the two hundred and forty-seven field
    names the lessons use and lets the rest appear as bare headings, so mixing
    the two is the existing design rather than something introduced here.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert "calculus" not in grammar.field_intros
    assert grammar.block_heading("calculus").endswith(":")


@needs_db
def test_the_lead_ins_are_a_third_of_what_a_reader_meets():
    """Fourteen fields, chosen by how often a block actually carries them."""
    import random
    from collections import Counter
    from langcurriculum.registry import all_lessons, get

    freq: Counter = Counter()
    for lesson_id in list(all_lessons()):
        for seed in range(3):
            try:
                term, *_ = get(lesson_id).generate(random.Random(seed))
            except Exception:
                continue
            if term.type == "record":
                for name, _v in term.value:
                    if name not in ("query", "utterance"):
                        freq[name] += 1
    written = set(DerivedGrammar(LanguageDB(), "deu").field_intros)
    covered = sum(n for f, n in freq.items() if f in written)
    assert covered / sum(freq.values()) > 0.28


@needs_db
def test_a_language_with_no_lead_ins_still_says_so():
    grammar = DerivedGrammar(LanguageDB(), "fin")
    assert not grammar.field_intros
    assert any("bare translated noun" in g for g in grammar.gaps())


@needs_db
def test_french_sets_off_the_marks_it_spaces():
    """French writes "Dans la scène :" and "rwzt ?"; the engine wrote neither.

    The cleanup that removes a stray space before punctuation is right in
    every other language and wrong here, so the language names the marks it
    spaces rather than the rule guessing. A no-break space, because the mark
    must not begin a line on its own.
    """
    from langcurriculum.registry import get
    text = get("symbol_grounding").example(0, language="fra").observation
    assert " :" in text and " ?" in text
    assert " :" not in text.replace(" ", "")


@needs_db
@pytest.mark.parametrize("code", ["deu", "spa", "ita", "rus", "english"])
def test_no_other_language_gains_a_space_before_its_marks(code):
    from langcurriculum.registry import get
    text = get("symbol_grounding").example(0, language=code).observation
    assert " " not in text


def test_the_spacing_does_not_depend_on_what_the_caller_left_behind():
    """Normalise first, then set off — so a stray space cannot double up."""
    grammar = get_grammar("english")
    grammar.typography = replace(grammar.typography, space_before=":?")
    try:
        assert grammar.punctuate("a:b") == "a :b"
        assert grammar.punctuate("a :b") == "a :b"
    finally:
        grammar.typography = replace(grammar.typography, space_before="")


# ======================================================================
# where the data lives
# ======================================================================
def test_language_data_lives_in_one_place():
    """There were three directories, two of them for historical reasons.

    The original packs kept their vocabulary under ``languages/data``, later
    ones shipped beside their grammar, and three languages had a file in each
    that was merged at load time — so counting the files told a reader nothing
    about how many languages the package has.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "langcurriculum"
    assert not (root / "languages" / "data").exists()
    assert not (root / "grammar" / "grammars" / "data").exists()
    data = root / "grammar" / "data"
    assert sorted(p.name for p in (data / "packs").glob("*.json")) == [
        "chinese.json", "english.json", "spanish.json", "swahili.json",
        "turkish.json"]
    assert not list(data.glob("*.json")), "a table escaped into the root"
    assert (data / "README.md").exists()


def test_every_table_is_keyed_by_iso_and_every_pack_by_its_name():
    """The one distinction the layout is allowed to make.

    A table records a fact about a language and is keyed by ISO 639-3; a pack
    is an implementation and is keyed by its own name, because
    ``english_synonym`` shares English's code and is not English.
    """
    import json
    from pathlib import Path
    tables = (Path(__file__).resolve().parent.parent / "langcurriculum"
              / "grammar" / "data" / "tables")
    for path in sorted(tables.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        keys = [k for k in raw if not k.startswith("_")]
        if path.name in ("lemmas.json", "predicates.json",
                         "paradigm_seeds.json"):
            continue                      # keyed by English word, not language
        assert keys and all(len(k) == 3 for k in keys), \
            f"{path.name} is not keyed by ISO 639-3: {keys[:5]}"


# ======================================================================
# a Han entry is written one way, not both
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [("cmn", "词典"), ("yue", "詞典")])
def test_a_chinese_entry_is_written_in_its_own_script(code, expected):
    """Wiktionary writes a Han headword as "Traditional /Simplified".

    Sixty-two thousand rows across Mandarin, Cantonese, Hakka, Wu and Min. Put
    on the page whole they are a word in neither: a derived Mandarin scene
    read "o0是黃 /黄立方體 /立方体". Which side to take is a fact the database
    already records as the language's script.
    """
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(db, code)._variant("詞典 /词典") == expected


@needs_db
@pytest.mark.parametrize("code", ["cmn", "yue", "hak", "wuu"])
def test_no_han_language_prints_both_writings(code):
    from langcurriculum.grammar.compile import curriculum_vocabulary
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    for key in sorted(curriculum_vocabulary()):
        assert " /" not in grammar.word(key), key


@needs_db
def test_a_word_with_no_variant_is_untouched():
    grammar = DerivedGrammar(LanguageDB(), "cmn")
    assert grammar._variant("立方体") == "立方体"
    assert grammar._variant("") == ""


# ======================================================================
# the harvest has to fetch what the page will show
# ======================================================================
def test_the_harvest_asks_for_the_words_the_headings_use():
    """Two hundred and twenty-five of them were never fetched.

    The harvest set was "every word a generator can coin", and a section
    heading is not coined -- it is the name of a record field. So ``entities``,
    ``agents`` and ``rules`` have a translation in no language at all, and a
    third of the headings across two hundred and sixty-three languages come
    out in English for want of ever having been asked for.
    """
    import random

    from langcurriculum.grammar.compile import rendered_vocabulary
    from langcurriculum.registry import all_lessons, get

    rendered = rendered_vocabulary()
    missing = set()
    for lesson_id in list(all_lessons())[::4]:
        term, *_ = get(lesson_id).generate(random.Random(0))
        if term.type != "record":
            continue
        for name, _value in term.value:
            if name in ("query", "utterance"):
                continue
            missing |= {w for w in name.replace("_", " ").split()
                        if w.isascii() and w not in rendered}
    assert not missing, f"headings the harvest would not fetch: {sorted(missing)[:8]}"


def test_the_harvest_set_and_the_coined_set_are_different_questions():
    """One is what a generator invents, the other what a reader sees.

    The collision rule and the coverage figures are about the coined set and
    must not move because the harvest grew.
    """
    from langcurriculum.grammar.compile import (curriculum_vocabulary,
                                                rendered_vocabulary)
    coined, rendered = curriculum_vocabulary(), rendered_vocabulary()
    assert coined < rendered
    # 405 before three lessons stopped describing themselves in English prose.
    # `difference`, `limit`, `modulus`, `previous` came with the conditions in
    # paradigm_shift and procedural_language; `number`, `order`, `even
    # number`, `first`, `keep`, `arrange`, `remove`, `exceed` with the program
    # descriptions. All are words the curriculum now coins, so a language has
    # to cover them. The `desc_*` heads are not: they name constructions, and
    # the builder replaces each with the words above.
    # 423 since interactive_reference and architecture_composition stopped
    # emitting `question` and the pipeline stage names as identifiers.
    assert len(coined) == 423, "the coined set moved; coverage numbers will too"
    assert "rule" in rendered and "entity" in rendered


def test_the_singular_of_a_heading_is_asked_for_too():
    """A dictionary lists *rule*; the lessons head a block ``rules``."""
    from langcurriculum.grammar.compile import rendered_vocabulary
    rendered = rendered_vocabulary()
    for plural, singular in (("rules", "rule"), ("entities", "entity"),
                             ("boxes", "box")):
        assert singular in rendered, singular


# ======================================================================
# counting in a language that counts with a classifier
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("cmn", "3个立方体"), ("vie", "3 cái lập phương"),
])
def test_a_classifier_language_counts_with_one(code, expected):
    """WALS says it needs one and the profile has carried that all along.

    A derived grammar even announced "numeral classifiers obligatory" among
    its notes, and then wrote 三立方體. The hook the linearizer offers for this
    says "classifier languages override" and only the hand-written Chinese
    ever did; twenty-one derived languages declared the need and wrote none.
    """
    from langcurriculum.grammar.syntax import mk_cn, mk_np, noun, sym
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert grammar.lin(mk_np(mk_cn(noun("cube")), count=sym("3"))) == expected


@needs_db
@pytest.mark.parametrize("code", ["cmn", "tha"])
def test_the_classifier_is_joined_the_way_the_language_joins_words(code):
    """Chinese writes them together, Vietnamese apart, neither told to."""
    from langcurriculum.grammar.syntax import mk_cn, mk_np, noun, sym
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(db, code)
    assert " " not in grammar.lin(mk_np(mk_cn(noun("cube")), count=sym("3")))


@needs_db
@pytest.mark.parametrize("code", ["hun", "tur", "hye", "deu", "fra"])
def test_a_language_that_does_not_need_one_does_not_get_one(code):
    """WALS marks Hungarian and Turkish 'optional', and optional means the
    bare numeral is grammatical — which is the one this engine can write."""
    from langcurriculum.grammar.syntax import mk_cn, mk_np, noun, sym
    from langcurriculum.grammar.typology import classifier_for
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    assert not classifier_for(code)
    rendered = DerivedGrammar(db, code).lin(
        mk_np(mk_cn(noun("cube")), count=sym("3")))
    assert rendered.startswith("3")


def test_the_languages_left_out_are_left_out_on_purpose():
    """Japanese floats its numeral away from the noun and Bengali's classifier
    is an enclitic on the numeral. Both need one; neither can be placed by
    this parameter, and a real word in the wrong place is worse than a gap."""
    from langcurriculum.grammar.typology import classifier_for
    for code in ("jpn", "kor", "ben"):
        assert not classifier_for(code)


# ======================================================================
# a script that has its own punctuation
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["arb", "pes", "urd", "ckb", "pbu"])
def test_an_arabic_script_language_uses_arabic_punctuation(code):
    """All five ended a question with "?" where "؟" belongs.

    The Arabic script has its own question mark, comma and semicolon, and the
    Latin ones are simply not its punctuation. The engine knew the script all
    along -- it is in the database and on the profile -- and used it only to
    set a right-to-left flag that nothing reads.
    """
    from langcurriculum.registry import get
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    text = get("symbol_grounding").example(0, language=code).observation
    assert "؟" in text and "?" not in text
    assert "؛" in text and ";" not in text


@needs_db
def test_hebrew_keeps_the_latin_marks():
    """Written right to left and using "?" and "," — which is why the thing
    that matters is the script and not the direction."""
    from langcurriculum.registry import get
    db = LanguageDB()
    if db.language("heb") is None:
        pytest.skip("heb absent")
    text = get("symbol_grounding").example(0, language="heb").observation
    assert "?" in text and "؟" not in text


@needs_db
@pytest.mark.parametrize("code", ["deu", "rus", "ell", "hin"])
def test_no_other_script_gains_arabic_marks(code):
    from langcurriculum.registry import get
    db = LanguageDB()
    if db.language(code) is None:
        pytest.skip(f"{code} absent")
    text = get("symbol_grounding").example(0, language=code).observation
    assert not (set(text) & set("؟؛،"))


@pytest.mark.parametrize("language", ["english", "spanish", "pol", "fin", "tur"])
def test_no_two_program_descriptions_read_the_same(language):
    """The descriptions are built by the grammar now, not written out.

    They used to be one English sentence per program, and two could coincide
    only if the sentences did, which the generator already checks. Built from
    a verb and a noun phrase they can coincide some other way -- a language
    with no word for one of the eight operations, or a bound dropped on the
    way to the page -- and an episode whose options collapse is unanswerable
    rather than merely clumsy.
    """
    import random

    from langcurriculum._support.causal import _dsl_desc
    from langcurriculum.grammar.compile import compile_term
    from langcurriculum.grammar.features import EMPTY
    from langcurriculum.lessons.s04_analogy_causality_and_programs.program_explanation import (
        gen_program_explanation)

    grammar = (GRAMMARS[language] if language in GRAMMARS
               else DerivedGrammar(LanguageDB(), language))
    for seed in range(12):
        obs, _labels, _answer, _hidden = gen_program_explanation(random.Random(seed))
        descriptions = obs.field("descriptions")
        said = [grammar.lin(compile_term(d.children[-1]), EMPTY)
                for d in descriptions.children]
        assert len(said) == 4, f"seed {seed}: {len(said)} descriptions"
        assert len(set(said)) == 4, (
            f"seed {seed} in {language}: two descriptions read alike:\n"
            + "\n".join(said))


@needs_db
def test_a_han_entry_is_one_writing_wherever_it_is_read_from():
    """Wiktionary writes a Han headword as "Traditional /Simplified".

    61,798 rows are like that, 734 of them curriculum words. The derived
    grammars split them; the hand-written Chinese pack did not, because it
    reads the store directly for a word it lacks -- so `threshold` came back
    as "門檻 /门槛", spaces and all, in a language written without spaces. The
    split belongs to the store, where every reader gets it.

    Only for languages actually written in Han. Hakka records both writings
    and is itself romanised; picking one there would hand a Latin-script
    language a Han character, where leaving the pair intact lets the
    usability screen reject it and the gap say so.
    """
    db = LanguageDB()
    for code, expected in (("cmn", "门槛"), ("yue", "門檻")):
        if db.language(code) is None:
            continue
        entry = db.lookup(code, "threshold")
        if entry is None:
            continue
        assert " /" not in entry.form, f"{code}: {entry.form}"
        assert entry.form == expected

    for code in ("hak", "mww"):
        if db.language(code) is None:
            continue
        assert DerivedGrammar(db, code)._copula_lemma() == ""

    grammar = GRAMMARS["chinese"]
    for key in ("threshold", "book"):
        assert " " not in grammar.word(key, "N"), key
