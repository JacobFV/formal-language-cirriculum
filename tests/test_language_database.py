"""Invariants of the data-backed languages.

These tests need the language database, which is two gigabytes and built from
public datasets rather than committed. They skip when it is absent, and the
skip message says how to build it — a test that silently passes because the data
is missing would be worse than no test.

What is asserted here is deliberately not "the output looks right". Nobody in
this repository speaks Basque, and a test written by someone who does not speak
a language can only check things that do not require speaking it:

* that the **word order matches what WALS coded**, per language, which is a
  factual claim checkable against a citation;
* that a language's **declared tier matches the data behind it**, so no language
  claims coverage it does not have;
* that **sense ranking** puts the primary meaning first, which is the difference
  between "big book" and "adult book" in a hundred languages at once;
* that the **morphology inducer** reproduces forms UniMorph attests, measured as
  held-out accuracy rather than asserted.
"""

from __future__ import annotations

import pytest

from langcurriculum.grammar.compile import curriculum_vocabulary
from langcurriculum.grammar.derived import DerivedGrammar
from langcurriculum.grammar.induce import (
    induce, parse_unimorph, unimorph_tags,
)
from langcurriculum.grammar.registry import REGISTRY
from langcurriculum.grammar.features import FS
from langcurriculum.grammar.store import LanguageDB
from langcurriculum.grammar.syntax import adj, mk_cn, mk_np, noun, pred_attr

from conftest import DB, needs_db


def np(key, *adjectives, **kw):
    return mk_np(mk_cn(noun(key), *[adj(a) for a in adjectives]), **kw)


# ======================================================================
# scale
# ======================================================================
@needs_db
def test_the_database_holds_what_the_readme_claims():
    t = DB.totals()
    assert t["wordforms"] > 10_000_000, t
    assert t["senses"] > 2_000_000, t
    assert t["profiles"] > 1_000, t


@needs_db
def test_enough_languages_carry_real_lexical_data():
    """The coverage claim, computed rather than asserted."""
    real = _dictionary_keys()
    buckets = {0.8: 0, 0.6: 0, 0.4: 0, 0.2: 0}
    for row in DB.languages(min_tier=4):
        pct = len(DB.bulk_lookup(row["code"], real)) / len(real)
        for threshold in buckets:
            if pct >= threshold:
                buckets[threshold] += 1
    # The claim the README makes, asserted against the data that backs it.
    assert buckets[0.8] >= 20, buckets
    assert buckets[0.6] >= 50, buckets
    assert buckets[0.4] >= 80, buckets
    assert buckets[0.2] >= 140, buckets


def _dictionary_keys() -> list[str]:
    """Curriculum keys that are English words, not coined identifiers.

    A third of what the generators coin — ``kb_fact``, ``astar``, ``dola`` —
    is not a word in any language and must pass through untranslated. Measuring
    coverage against the whole key set would understate every language by the
    same third and make the number meaningless.
    """
    keys = sorted(curriculum_vocabulary())
    marks = ",".join("?" * len(keys))
    return [r["key"] for r in DB.conn.execute(
        f"SELECT DISTINCT key FROM sense WHERE key IN ({marks})", keys)]


# ======================================================================
# typology drives the grammar
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,clause", [
    ("jpn", "SOV"), ("tur", "SOV"), ("hin", "SOV"), ("kor", "SOV"),
    ("eus", "SOV"), ("kat", "SOV"), ("ben", "SOV"),
    ("deu", "SVO"), ("rus", "SVO"), ("swh", "SVO"), ("vie", "SVO"),
    ("arb", "VSO"), ("cym", "VSO"), ("gle", "VSO"),
])
def test_clause_order_matches_the_wals_coding(code, clause):
    """WALS 81A is a citable claim about the language; the grammar must honour it."""
    if DB.language(code) is None:
        pytest.skip(f"{code} not in the database")
    assert DerivedGrammar(DB, code).order.clause == clause


@needs_db
@pytest.mark.parametrize("code,side", [
    ("fra", "NA"), ("spa", "NA"), ("arb", "NA"), ("vie", "NA"), ("swh", "NA"),
    ("deu", "AN"), ("rus", "AN"), ("jpn", "AN"), ("tur", "AN"), ("hun", "AN"),
])
def test_adjective_side_matches_the_wals_coding(code, side):
    if DB.language(code) is None:
        pytest.skip(f"{code} not in the database")
    assert DerivedGrammar(DB, code).order.adj == side


@needs_db
def test_a_language_without_articles_does_not_acquire_one():
    """Wiktionary will happily translate "the" into a demonstrative. WALS 37A
    says whether the language has an article, and it wins."""
    for code in ("rus", "hin", "jpn", "fin"):
        if DB.language(code) is None:
            continue
        grammar = DerivedGrammar(DB, code)
        if not grammar._params.get("has_definite"):
            assert grammar.cw("the") == "", code


# ======================================================================
# sense ranking
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,key,expected", [
    ("hun", "big", "nagy"),        # not felnőtt "adult"
    ("spa", "big", "grande"),      # not mayor "elder"
    ("fin", "big", "iso"),         # not aikuinen "adult"
])
def test_the_primary_sense_wins(code, key, expected):
    """Wiktionary's own order puts "big = grown-up" first for these languages.

    Ranking senses by how many languages translate them recovers the meaning a
    reader expects, and it does so for every language at once rather than by a
    per-language correction nobody could maintain.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} not in the database")
    entry = DB.lookup(code, key, "A")
    assert entry is not None and entry.form == expected


# ======================================================================
# morphology induction
# ======================================================================
@needs_db
@pytest.mark.parametrize("code", ["tur", "fin", "hun", "spa", "deu"])
def test_induced_morphology_reproduces_held_out_forms(code):
    """Train on most of a language's paradigms, then predict the rest.

    This is the only honest way to check an inducer: asserting a handful of
    hand-picked forms measures whether the author knew the language, not whether
    the model generalizes. Held-out accuracy measures the thing itself.
    """
    if DB.language(code) is None or not DB.language(code)["n_forms"]:
        pytest.skip(f"{code} has no UniMorph data")
    # One source, as DataMorphology._training does. Pooling two annotation
    # schemes puts incompatible labellings behind one cell key and halves
    # accuracy — which is why the engine does not do it, and why a test that
    # did would be measuring something the engine never runs.
    rows = [(r["lemma"], r["surface"], r["feats"]) for r in DB.conn.execute(
        "SELECT lemma, surface, feats FROM wordform "
        "WHERE code=? AND pos='N' AND source='unimorph' LIMIT 40000", (code,))]
    if len(rows) < 2000:
        pytest.skip(f"{code} has too few nominal forms to split")
    train, test = rows[:-1000], rows[-1000:]
    paradigms = induce(train)
    assert paradigms, f"{code}: nothing induced from {len(train)} forms"

    hits = total = 0
    for lemma, surface, bundle in test:
        feats = parse_unimorph(bundle)
        if feats is None:
            continue
        cell = paradigms.get(unimorph_tags(bundle))
        if cell is None:
            continue
        total += 1
        hits += cell.inflect(lemma) == surface
    if total < 50:
        pytest.skip(f"{code}: too few comparable held-out cells")
    accuracy = hits / total
    assert accuracy >= 0.55, \
        f"{code}: induced morphology only {accuracy:.0%} accurate on {total} cells"


@needs_db
def test_the_inducer_recovers_turkish_vowel_harmony_without_being_told():
    """The point of conditioning on stem endings, stated as a test.

    Turkish plurals are ``-lar`` after a back vowel and ``-ler`` after a front
    one. An inducer that learned one rule per cell would get half of them wrong;
    one indexed on what the stem ends with gets both, having never heard of
    harmony.
    """
    rows = [(r["lemma"], r["surface"], r["feats"]) for r in DB.conn.execute(
        "SELECT lemma, surface, feats FROM wordform WHERE code='tur' AND pos='N' "
        "AND source='unimorph' LIMIT 60000")]
    if len(rows) < 1000:
        pytest.skip("no Turkish nominal data")
    paradigms = induce(rows)
    plural = [p for tags, p in paradigms.items()
              if tags == frozenset({"NOM", "PL"}) or tags == frozenset({"PL"})]
    if not plural:
        pytest.skip("no bare plural cell attested")
    cell = plural[0]
    assert cell.inflect("ev").endswith("ler"), cell.inflect("ev")
    assert cell.inflect("kitap").endswith("lar"), cell.inflect("kitap")


# ======================================================================
# honesty
# ======================================================================
@needs_db
def test_every_language_tier_matches_the_data_behind_it():
    """A tier is a claim about evidence. It must be checkable, and checked."""
    for row in DB.languages(min_tier=4):
        tier, senses, forms = row["tier"], row["n_senses"], row["n_forms"]
        if tier == 2:
            assert forms >= 1000 and senses >= 200, dict(row)
        elif tier == 3:
            assert senses >= 200, dict(row)


@needs_db
def test_a_derived_grammar_states_its_gaps():
    for code in ("deu", "jpn", "swh", "tam"):
        if DB.language(code) is None:
            continue
        grammar = DerivedGrammar(DB, code)
        assert any("NOT attempted" in n for n in grammar.notes), code
        assert isinstance(grammar.gaps(), list)


@needs_db
def test_a_handwritten_grammar_outranks_the_derived_one_for_its_language():
    """Turkish has both. The verified one must win, or verification is pointless."""
    import langcurriculum.grammar.grammars as G      # noqa: F401  (registers them)
    assert REGISTRY.get("tur") is REGISTRY.get("turkish")
    assert REGISTRY.tier_of("turkish") == 1


@needs_db
def test_provenance_is_recorded_for_every_row():
    for code in ("deu", "tur", "swh"):
        sources = DB.provenance(code)
        assert sources, code
        assert all(":" in k and v > 0 for k, v in sources.items()), sources


# ======================================================================
# end to end
# ======================================================================
@needs_db
def test_a_real_lesson_renders_in_many_languages():
    import langcurriculum as lc
    lesson = lc.get("symbol_grounding")
    rendered = 0
    for code in [r["code"] for r in DB.languages(min_tier=3)][:400]:
        try:
            example = lesson.example(0, language=code)
        except Exception:
            continue
        if example.prompt.strip():
            rendered += 1
    assert rendered >= 250, f"only {rendered} languages rendered"


@needs_db
@pytest.mark.parametrize("code", ["deu", "spa", "rus", "jpn", "tur", "swh", "arb"])
def test_no_internal_representation_leaks_into_a_derived_rendering(code):
    import re
    import langcurriculum as lc
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    leaked = re.compile(r"\?[a-z]+#\d+|FS\(|Var\(|Node\(|<[a-z]+ object")
    for lid in ("symbol_grounding", "finite_state_language"):
        text = lc.get(lid).example(0, language=code).prompt
        hit = leaked.search(text)
        assert hit is None, f"{code}/{lid} leaked {hit.group(0)!r}"


# ======================================================================
# derived-grammar quality, from data rather than authoring
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,key,expected", [
    ("deu", "book", "das Buch"),      # neuter — der Buch was the bug
    ("deu", "tree", "der Baum"),      # masculine
    ("spa", "house", "la casa"),      # feminine
    ("spa", "book", "el libro"),      # masculine
    ("ita", "book", "il libro"),
    ("por", "house", "a casa"),
])
def test_the_article_agrees_using_the_dictionary_s_own_gender_tags(code, key, expected):
    """Wiktionary tags *der* masculine and *das* neuter. Reading that is enough.

    No per-language article table is authored anywhere: the paradigm that tells
    *das Buch* from *der Buch* is already in the translation data.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(DB, code).lin(np(key, det="def")) == expected


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("deu", "ist"), ("spa", "es"), ("fra", "est"), ("ita", "è"), ("por", "é"),
    ("nld", "is"), ("swe", "är"), ("dan", "er"), ("ces", "je"), ("rus", "есть"),
    ("bul", "е"), ("ron", "este"), ("ell", "είναι"), ("hun", "van"),
    ("fin", "on"), ("cat", "és"), ("lit", "yra"),
])
def test_the_copula_is_identified_without_a_per_language_table(code, expected):
    """Seventeen languages, no hand-written copula list anywhere.

    Wiktionary lists several verbs under *be* with nothing to separate them —
    German *werden* beside *sein*, Italian *venire* beside *essere*. Three
    signals do it, and all three are facts about frequency rather than about
    any particular language: the copula is the **shortest** finite form (Zipf),
    the most **suppletive** (it shares almost nothing with its own infinitive),
    and where those tie the dictionary's own **primary sense** decides.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    from langcurriculum.grammar.features import EMPTY
    assert DerivedGrammar(DB, code).copula("attr", EMPTY) == expected


@needs_db
def test_wiktionary_supplies_the_paradigms_unimorph_omits():
    """The gap this harvest exists to close, asserted directly.

    UniMorph is a paradigm resource and the copula does not have a paradigm so
    much as a list, so *ist*, *есть* and *è* are absent from files running to
    hundreds of thousands of forms. Wiktionary's inflection tables have them.
    """
    for code, lemma, surface in (("deu", "sein", "ist"), ("rus", "быть", "есть"),
                                 ("ita", "essere", "è")):
        if DB.language(code) is None:
            continue
        um = [s for f, s in DB.paradigm(code, lemma)]
        assert surface in um, f"{code}/{lemma} is missing {surface}"
        source = DB.conn.execute(
            "SELECT source FROM wordform WHERE code=? AND surface=? LIMIT 1",
            (code, surface)).fetchone()
        assert source["source"] == "wiktionary", dict(source)


@needs_db
def test_no_paradigm_cell_is_a_phrase():
    """Wiktextract emits periphrastic cells and parse artefacts beside real ones.

    Czech *byla by* and Hungarian *lenne or* both won an attested-cell lookup
    before this was filtered, and the engine inflects words, not phrases.
    """
    n = DB.conn.execute(
        "SELECT COUNT(*) FROM wordform WHERE surface LIKE '% %'").fetchone()[0]
    assert n == 0, f"{n} paradigm cells are phrases"


@needs_db
def test_a_grammar_that_cannot_find_a_copula_paradigm_says_so():
    """Stated as a property, not against a named language.

    Russian used to be the example — its copula was missing until Wiktionary's
    tables were harvested. Pinning a test to one language means it silently
    stops testing anything the moment that language is fixed, so the invariant
    is written over whichever languages currently lack a paradigm.
    """
    from langcurriculum.grammar.features import EMPTY
    checked = 0
    for row in DB.languages(min_tier=2)[:40]:
        grammar = DerivedGrammar(DB, row["code"])
        if not grammar.order.copula_overt:
            continue
        from langcurriculum.grammar.typology import copula_for
        if copula_for(row["code"]) is not None:
            continue                      # written down and checked, not guessed
        lemma = grammar._copula_lemma()
        if DB.paradigm(row["code"], lemma):
            continue                      # it has one; nothing to declare
        checked += 1
        assert any("copula" in g for g in grammar.gaps()), \
            f"{row['code']} has no copula paradigm and does not say so"
    if not checked:
        pytest.skip("every language checked now has a copula paradigm")


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("deu", "Szene"), ("spa", "escena"), ("rus", "Сце́на"), ("fin", "Näyttämö"),
])
def test_section_headings_are_in_the_language(code, expected):
    """"Scene:" in a German episode is the most visible artefact there is."""
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    heading = DerivedGrammar(DB, code).block_heading("scene")
    assert expected.lower() in heading.lower(), heading


@needs_db
def test_a_grammar_without_idiomatic_lead_ins_still_says_so():
    """A translated noun is better than an English one and still not idiomatic."""
    if DB.language("deu") is None:
        pytest.skip("deu absent")
    assert any("idiomatic" in g for g in DerivedGrammar(DB, "deu").gaps())


# ======================================================================
# the indefinite article
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,expected", [
    ("deu", "ein"), ("fra", "un"), ("por", "um"),
    ("swe", "en"), ("cat", "un"), ("tur", "bir"),
])
def test_the_indefinite_article_comes_from_one_not_from_a(code, expected):
    """The key matters more than the algorithm.

    Looking up English *a* asks a dictionary about the letter A and the musical
    note, and that is what it answers: German came out with *A* and *den*. The
    indefinite article is a worn-down numeral in most languages that have one —
    which is exactly what WALS 38A code 2 records — so *one* is the key that
    retrieves *ein*, *un*, *um*, *een*, *bir*.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(DB, code).cw("a") == expected


@needs_db
@pytest.mark.parametrize("code", ["pol", "ces", "rus", "fin"])
def test_a_language_with_no_indefinite_article_never_acquires_one(code):
    """WALS says these have none, so no amount of dictionary data may add one."""
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(DB, code).cw("a") == ""


@needs_db
@pytest.mark.parametrize("code", ["jpn", "nld", "hun"])
def test_an_indefinite_word_distinct_from_one_is_left_out_and_declared(code):
    """WALS 38A code 1 means an indefinite word exists and is *not* the numeral.

    Which word it is, nothing here knows. Japanese would otherwise be given
    一つ — "one thing", a counter phrase, not an article. The cost is real and
    accepted: Dutch *een* and Hungarian *egy* would have been right and are
    dropped too. Preferring a visible gap to a confident guess is the trade this
    package makes everywhere, and making it selectively would mean deciding by
    eye which languages to trust.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(DB, code)
    assert grammar.cw("a") == ""
    assert any("distinct from the numeral" in g for g in grammar.gaps())


@needs_db
def test_the_impersonal_pronoun_sense_of_one_is_not_mistaken_for_an_article():
    """*One does not simply…* translates to je, se, men, man — all short.

    Choosing by length alone picked them. They are distinguishable because the
    numeral senses carry a Card part of speech and the pronoun senses carry
    none.
    """
    for code, wrong in (("nld", "je"), ("ron", "se"), ("dan", "man")):
        if DB.language(code) is None:
            continue
        assert DerivedGrammar(DB, code).cw("a") != wrong


@needs_db
def test_no_closed_class_slot_holds_an_affix_or_an_english_leak():
    """Finnish has a case, not a preposition, and offered ``-lla`` for *at*.

    It was printed as its own token. An affix, a phrase and an untranslated
    English word are all things a translation table will hand back, and none of
    them is a word of the language.
    """
    for row in DB.languages(min_tier=2)[:30]:
        grammar = DerivedGrammar(DB, row["code"])
        for slot, form in grammar.closed.items():
            if not form:
                continue
            assert not form.startswith("-") and not form.endswith("-"), \
                f"{row['code']}/{slot} is the affix {form!r}"
            assert " " not in form, f"{row['code']}/{slot} is the phrase {form!r}"


# ======================================================================
# adjective agreement
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,key,expected", [
    ("deu", "cube", "ein gelber Kubus"),     # masculine
    ("deu", "house", "ein gelbes Haus"),     # neuter — the strong/mixed -es
    ("spa", "house", "una casa amarilla"),
    ("ita", "house", "una casa gialla"),
    ("por", "house", "uma casa amarela"),
    ("swe", "house", "ett gult hus"),        # neuter -t
    ("ell", "house", "ένα κίτρινο σπίτι"),
])
def test_the_attributive_adjective_agrees_with_its_noun(code, key, expected):
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    got = DerivedGrammar(DB, code).lin(np(key, "yellow", det="indef"))
    # the article allomorph is a separate concern; the adjective is what is asserted
    assert got.split()[-2:] == expected.split()[-2:], f"{got!r} vs {expected!r}"


@needs_db
def test_concord_is_switched_on_by_evidence_where_wals_did_not_code_it():
    """WALS 30A is *absent* for Italian, Portuguese, Polish and Czech.

    Reading a missing feature as "no genders" switched concord off for five
    major languages that plainly have it. Tens of thousands of their nouns carry
    a gender tag, which settles the question from evidence.
    """
    for code in ("ita", "por", "ron", "ces"):
        if DB.language(code) is None:
            continue
        grammar = DerivedGrammar(DB, code)
        assert "30A" not in (grammar._params.get("evidence") or {}), \
            f"{code}: WALS now codes 30A, so this test is measuring nothing"
        assert grammar.concord.adjective, f"{code} should have concord on evidence"


@needs_db
@pytest.mark.parametrize("code,lemma", [
    ("ita", "casa"), ("spa", "casa"), ("por", "casa"), ("deu", "Haus"),
])
def test_a_noun_is_never_inflected_for_its_own_gender(code, lemma):
    """A noun *has* a class; it does not decline for one.

    Asking the inflector for a masculine *casa* sends it looking for a cell that
    cannot exist, and the analogical fallback invents *casessa*.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(DB, code)
    for gender in ("m", "f", "n"):
        # nominative singular, as _np_features supplies in the real walk: an
        # unspecified case does not disagree with a genitive cell
        got = grammar.inflect("N", lemma,
                              FS({"cls": gender, "num": "sg", "case": "nom"}))
        assert got == lemma, f"{code}: {lemma} became {got!r} for cls={gender}"


@needs_db
def test_a_paradigm_that_lacks_a_cell_falls_back_to_the_citation_form():
    """Wiktextract omits the cell that equals the lemma, and that silence is data.

    Spanish lists *amarilla*, *amarillos*, *amarillas* and not *amarillo*, so a
    masculine-singular request matches nothing. Analogizing there produced
    *amarillos*; the unmarked cell is the citation form.
    """
    grammar = DerivedGrammar(DB, "spa")
    assert grammar.inflect("A", "amarillo",
                           FS({"cls": "m", "num": "sg", "case": "nom"})) == "amarillo"


# ======================================================================
# English leakage: the metric, kept as a ceiling
# ======================================================================
def _leakage(code: str, n_lessons: int = 30) -> tuple[float, list[str]]:
    """What fraction of an episode's words are untranslated English.

    Counts only words the reference vocabulary knows *and* that the target
    language has an entry for, so a genuine coverage gap is not scored as a
    defect. Proper names are excluded: *alice* and *frank* are supposed to pass
    through, and counting them would put a floor under every language.
    """
    import re
    from langcurriculum.grammar.compile import _english, curriculum_vocabulary

    keys = sorted(curriculum_vocabulary())
    marks = ",".join("?" * len(keys))
    known = {r["key"] for r in DB.conn.execute(
        f"SELECT DISTINCT key FROM sense WHERE key IN ({marks})", keys)}
    known -= set(_english().names)
    # A key whose translation *is* the key is not evidence of anything. German
    # capitalizes its nouns, so *agent* renders as ``Agent`` and a
    # case-insensitive scan counted the correct output as a leak; several
    # technical terms are likewise borrowed unchanged. Comparing against what
    # the language actually renders removes a false positive that was worth
    # roughly a point of apparent leakage in every language.
    grammar = DerivedGrammar(DB, code)
    known = {k for k in known if grammar.word(k).lower() != k.lower()}

    import langcurriculum as lc
    lessons = [l for l in lc.all_lessons().values()
               if l.status == "implemented"][:n_lessons]
    leaked: dict[str, int] = {}
    total = 0
    for lesson in lessons:
        for word in re.findall(r"[a-z]{3,}",
                               lesson.example(0, language=code).observation.lower()):
            total += 1
            if word in known:
                leaked[word] = leaked.get(word, 0) + 1
    fraction = sum(leaked.values()) / max(total, 1)
    worst = sorted(leaked, key=leaked.get, reverse=True)[:8]
    return fraction, worst


@needs_db
@pytest.mark.parametrize("code,ceiling", [
    ("deu", 0.04), ("spa", 0.04), ("ita", 0.03), ("swe", 0.06),
    ("nld", 0.04), ("fra", 0.07), ("por", 0.06), ("rus", 0.07),
])
def test_english_leakage_stays_under_its_ceiling(code, ceiling):
    """A ceiling, not a target — it exists to catch regressions.

    These began at 15–30%: every word outside the three inflecting classes was
    treated as an opaque symbol and printed in English in all four hundred
    languages. The ceilings sit about a third above the current measurement, so
    ordinary variation passes and a structural regression does not. They are
    sample-size dependent — a different ``n_lessons`` gives different numbers —
    so they were measured with exactly the call this test makes.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    fraction, worst = _leakage(code)
    assert fraction <= ceiling, \
        f"{code}: {fraction:.1%} English (ceiling {ceiling:.0%}); worst: {worst}"


@needs_db
def test_a_word_outside_the_inflecting_classes_is_still_translated():
    """The bug the ceiling exists to prevent, stated directly.

    ``colour``, ``yes``, ``size`` and ``above`` live in the reference
    vocabulary's fourth table, outside noun/adjective/verb. They were classified
    as symbols, and a symbol is never translated.
    """
    from langcurriculum.grammar.compile import classify
    for word in ("color", "yes", "size", "above", "true"):
        assert classify(word) == "word", word
    grammar = DerivedGrammar(DB, "deu")
    assert grammar.word("color") != "color"


@needs_db
def test_a_bare_colour_argument_is_translated():
    """``(obj o3 red 4 6)`` — "o3 is red" — kept the English word.

    A non-noun argument fell through to an opaque symbol, so every predicate
    whose value was a colour rather than a shape stayed in English.
    """
    from langcurriculum.grammar.compile import _as_np
    grammar = DerivedGrammar(DB, "deu")
    assert grammar.lin(_as_np("red")) != "red"


@needs_db
@pytest.mark.parametrize("code,slot", [
    ("deu", "trial"), ("rus", "round"), ("fra", "turn"), ("spa", "round"),
])
def test_an_ordinal_row_label_is_looked_up_as_a_noun(code, slot):
    """*step 4*, *round 2*, *trial 7* — the label is a noun in that use.

    Left untyped, the dictionary answers with whichever sense it lists first:
    German *round* gives ``rund`` "circular" and *turn* gives a verb. Naming the
    part of speech is the whole fix, and it is the same lesson as the copula and
    the indefinite article — the retrieval key matters more than the algorithm.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(DB, code)
    form = grammar.cw(slot)
    assert form and form != slot, f"{code}/{slot} did not translate"
    typed = DB.lookup(code, slot, "N")
    assert typed is not None and form == typed.form


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("fra", "valeur de"), ("spa", "valor de"),
])
def test_a_multi_word_label_is_translated_token_by_token(code, expected):
    """No dictionary has an entry for *value of*, but it has one for each word.

    A literal rendering in the right language beats a fluent one in the wrong
    language, and these labels were passing through wholly in English.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(DB, code).word("value of") == expected


@needs_db
def test_a_phrase_of_unknown_words_is_left_intact():
    """Half-translating is worse than not translating.

    A label whose tokens the language has no entry for must come back whole,
    not as a mixture of the two languages.
    """
    grammar = DerivedGrammar(DB, "deu")
    assert grammar.word("bfs astar") == "bfs astar"


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("fra", "vert bleu vert"), ("spa", "verde azul verde"),
])
def test_a_whole_sequence_given_as_one_string_is_translated(code, expected):
    """Some generators build a sequence as a single ``str`` term.

    A few-shot lesson shows ``zrv nzrn ppk → green blue green`` with both sides
    as one string each. As opaque symbols neither was translated, and the second
    is ordinary vocabulary every language in the database has.
    """
    from langcurriculum.grammar.compile import _leaf
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(DB, code).lin(_leaf("green blue green")) == expected


@needs_db
@pytest.mark.parametrize("nonce", ["zrv nzrn ppk", "bfs astar", "kes kirn bex"])
def test_a_coined_sequence_is_never_translated(nonce):
    """All-or-nothing, and this is the half that matters.

    The coined half of a few-shot episode is what the lesson turns on. Touching
    any of it — even one token that happens to collide with a real word —
    would destroy the task.
    """
    from langcurriculum.grammar.compile import _leaf
    for code in ("deu", "fra", "rus"):
        if DB.language(code) is None:
            continue
        assert DerivedGrammar(DB, code).lin(_leaf(nonce)) == nonce


# ======================================================================
# reading one annotation scheme, per lemma
# ======================================================================
@needs_db
@pytest.mark.parametrize("code,lemma,expected", [
    ("fin", "kuutio", "kuutio"), ("hun", "kocka", "kocka"),
    ("deu", "Haus", "Haus"),
    # not Polish *dom*: inflect() takes the English key, and "dom" happens to be
    # an English word, so it resolves to a Polish translation before any
    # morphology runs. A test lemma has to be one English does not also have.
])
def test_an_unmarked_request_returns_the_citation_form(code, lemma, expected):
    """The unmarked cell is the lemma, and the loader omits it.

    Wiktextract skips the row equal to the headword, so a plain nominative
    singular can never match exactly and whatever it does match is
    over-specified. Finnish answered ``kuutioni`` — "my cube" — because a
    possessive was the closest thing left in the table.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    grammar = DerivedGrammar(DB, code)
    assert grammar.inflect("N", lemma, FS({"num": "sg", "case": "nom"})) == expected


@needs_db
@pytest.mark.parametrize("code,lemma,feats,expected", [
    ("fin", "kuutio", {"num": "pl", "case": "nom"}, "kuutiot"),
    ("fin", "kuutio", {"num": "sg", "case": "ine"}, "kuutiossa"),
    ("deu", "Haus", {"num": "pl", "case": "nom"}, "Häuser"),
])
def test_a_marked_request_still_inflects(code, lemma, feats, expected):
    """The citation-form shortcut must not swallow genuine inflection."""
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    assert DerivedGrammar(DB, code).inflect("N", lemma, FS(feats)) == expected


@needs_db
def test_the_two_annotation_schemes_are_never_pooled_for_one_lemma():
    """Swedish *gult* came back *gulare* from a Wiktionary row missing its degree.

    UniMorph tags the comparative ``ADJ;CMPR;NEUT;SG;INDF``; Wiktionary emits the
    same form as ``A;INDF;NEUT;SG`` with the degree dropped. Pooled, the
    untagged row answers a request for the plain adjective.
    """
    grammar = DerivedGrammar(DB, "swe")
    assert grammar.inflect("A", "gul",
                           FS({"cls": "n", "num": "sg", "case": "nom"})) == "gult"


@needs_db
@pytest.mark.parametrize("code,expected", [
    ("swe", "är"), ("deu", "ist"), ("rus", "есть"), ("dan", "er"),
])
def test_the_scheme_is_chosen_per_lemma_not_per_language(code, expected):
    """Choosing once for a whole language is wrong in the other direction.

    UniMorph systematically omits suppletive auxiliaries, so a language that
    "has UniMorph" still has no copula there. Preferring it globally lost *ist*,
    *är* and *есть* — the very forms the second source was harvested to supply.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    from langcurriculum.grammar.features import EMPTY
    assert DerivedGrammar(DB, code).copula("attr", EMPTY) == expected


# ======================================================================
# an episode must stay answerable in every language
# ======================================================================
def _four_claims(grammar):
    """The four quantified claims a formalization episode asks a learner to tell apart."""
    from langcurriculum.grammar.compile import _as_np
    from langcurriculum.grammar.syntax import adj, mk_ap, quant
    return [grammar.sentence(grammar.lin(
                quant(q, _as_np("prism", det="bare"),
                      mk_ap(adj("yellow"))).but(pol=pol)))
            for q, pol in (("all", "pos"), ("all", "neg"),
                           ("some", "pos"), ("some", "neg"))]


@needs_db
def test_no_language_collapses_two_distinct_claims():
    """The strongest correctness property this package has, over all 404 languages.

    ``deformalization`` hands a learner four glosses and asks which matches a
    formula. If two of them render alike the episode is not clumsy, it is
    **unanswerable** — and it fails silently, because a missing negator does not
    look like an error, it looks like a positive sentence.

    French had exactly that: its dictionary lists the discontinuous *ne … pas*
    first, no single slot could hold it, and "every prism is yellow" and "no
    prism is yellow" came out identical.
    """
    collapsed = []
    for row in DB.languages(min_tier=3):
        try:
            grammar = DerivedGrammar(DB, row["code"])
        except Exception:
            continue
        forms = _four_claims(grammar)
        if len(set(forms)) < 4:
            collapsed.append((row["code"], forms))
    assert not collapsed, (
        f"{len(collapsed)} languages render two different claims alike: "
        + "; ".join(f"{c}: {f[0]!r} == {f[1]!r}" for c, f in collapsed[:5]))


@pytest.mark.parametrize("code", ["english", "spanish", "chinese", "turkish", "swahili"])
def test_the_hand_written_grammars_keep_the_claims_apart_too(code):
    from langcurriculum.grammar.grammars import get_grammar
    forms = _four_claims(get_grammar(code))
    assert len(set(forms)) == 4, f"{code}: {forms}"


@needs_db
def test_a_negator_is_never_empty():
    """A missing negator turns a negative claim into a positive one.

    Where a language has no dedicated word the negative determiner stands in,
    and where that is absent too the English word does. A visibly foreign
    negator is a small problem; a vanished one changes what the episode says.
    """
    for row in DB.languages(min_tier=3)[:60]:
        try:
            grammar = DerivedGrammar(DB, row["code"])
        except Exception:
            continue
        assert grammar.negator(), f"{row['code']} has no negator at all"


# ======================================================================
# the answer set, in every language
# ======================================================================
#: A spread of typologies rather than a spread of families: verb-final and
#: verb-initial, case-marking and not, three scripts, one classifier language.
_ANSWER_SET_LANGUAGES = ["deu", "fra", "spa", "ita", "rus", "jpn", "fin", "ell"]


@needs_db
@pytest.mark.parametrize("code", _ANSWER_SET_LANGUAGES)
def test_translating_the_options_never_merges_two_of_them(code):
    """The counterpart of the negation-collapse check, on the answer side.

    An episode whose *prompt* renders two claims alike is unanswerable; so is one
    whose *options* do. The existing guard covered only the hand-written
    grammars, which is the half least likely to fail — a derived language
    translates its options through a scraped dictionary, where two English words
    landing on one target word is exactly what happens.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    import langcurriculum as lc
    collapsed = []
    for lesson in [l for l in lc.all_lessons().values()
                   if l.status == "implemented"][::2]:
        example = lesson.example(0, language=code)
        if len(set(example.choices)) != len(example.choices):
            collapsed.append(lesson.id)
        elif example.answer not in example.choices:
            collapsed.append(f"{lesson.id} (answer not among options)")
    assert not collapsed, f"{code}: {collapsed[:5]}"


@needs_db
@pytest.mark.parametrize("code", _ANSWER_SET_LANGUAGES)
def test_the_same_option_is_correct_in_every_language(code):
    """The curriculum's central cross-language invariant, stated positionally.

    A language changes the words and never the answer. Checking the *text* of
    the answer cannot show this, because the text is supposed to differ; what
    must hold is that the correct option occupies the same position, so a score
    obtained in one language is comparable with a score obtained in another.
    """
    if DB.language(code) is None:
        pytest.skip(f"{code} absent")
    import langcurriculum as lc
    for lesson in [l for l in lc.all_lessons().values()
                   if l.status == "implemented"][::2]:
        base = lesson.example(0, language="english")
        if base.answer not in base.choices:
            continue
        index = base.choices.index(base.answer)
        other = lesson.example(0, language=code)
        assert len(other.choices) == len(base.choices), \
            f"{code}/{lesson.id}: {len(other.choices)} options vs {len(base.choices)}"
        assert other.choices[index] == other.answer, \
            f"{code}/{lesson.id}: the correct option moved from position {index}"
