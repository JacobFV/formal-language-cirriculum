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

    grammar = DerivedGrammar(LanguageDB(), code)
    rendered: dict[str, str] = {}
    for key in sorted(curriculum_vocabulary()):
        for pos in ("N", "A", "V"):
            form = grammar.lookup(key, pos)
            if not form:
                continue
            clash = rendered.get((form.lower(), pos))
            assert clash is None, \
                f"{code}: {key!r} and {clash!r} both render as {form!r} ({pos})"
            rendered[(form.lower(), pos)] = key


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
