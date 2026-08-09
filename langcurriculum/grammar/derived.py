"""Grammars assembled from data rather than written by hand.

A hand-written grammar — :mod:`~langcurriculum.grammar.grammars.turkish` is the
model — states its parameters, supplies a lexicon, and overrides the handful of
things its language does that the parameters cannot express. Writing one takes a
day and knowing whether it is *right* takes a speaker.

A **derived** grammar takes the same parameters from WALS, the same lexicon from
Wiktionary, and the same morphology from UniMorph, and assembles the object
automatically. It has no overrides, because nobody has looked at it. That is the
whole difference, and it is the reason derived grammars are labelled tier 2–4 and
hand-written ones tier 1: the machinery is identical, the *verification* is not.

What a derived grammar gets right
---------------------------------

Word order, adposition side, article inventory, alignment, concord presence,
classifier requirement, and inflection for any lemma UniMorph attests — all from
sources that coded them deliberately. For a language with dense coverage this is
a genuinely usable rendering.

What it gets wrong, and says so
-------------------------------

It has no phonology, so it cannot know that a Turkish suffix harmonizes; the
inducer recovers that statistically from stem endings, which works for the
attested inventory and degrades on novel stems. It has no idiomatic lead-ins, so
a section heading is the English field name until someone supplies one. It
cannot know that Turkish drops its copula, because WALS does not code copula
omission. Each of these is visible in :meth:`DerivedGrammar.gaps`, and the tests
assert that a grammar's declared tier matches what its data actually supports.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .category import A, ADV, CLS, N, NUM, V
from .features import EMPTY, FS
from .induce import DataMorphology
from .linearize import (
    ERG_ABS, NOM_ACC, NO_CASE, Alignment, Concord, Grammar, Typography,
    WordOrder,
)
from .store import LanguageDB

__all__ = ["DerivedGrammar", "CLOSED_CLASS_KEYS"]

_ALIGNMENTS = {"NOM_ACC": NOM_ACC, "ERG_ABS": ERG_ABS, "NO_CASE": NO_CASE}


def _shared_prefix(lemma: str, form: str) -> int:
    """How much of its own lemma an inflected form keeps.

    Near zero for a suppletive paradigm, which is what a copula has.
    """
    n = 0
    for a, b in zip(lemma.lower(), form.lower()):
        if a != b:
            break
        n += 1
    return n

#: The engine's closed-class slots, and the English lemma whose Wiktionary
#: translation table supplies each. These are ordinary dictionary entries, so
#: the closed class comes from exactly the same source as the open one rather
#: than from a per-language table somebody would have to write a hundred times.
#: the character ranges each script occupies, for rejecting a translation
#: written in the wrong one — Romanian is listed with a Cyrillic *уну* beside
#: the Latin *unu*, and a Cyrillic article in a Latin-script episode is simply
#: the wrong row
_SCRIPT_RANGES = {
    "Cyrl": ("\u0400", "\u04ff"), "Grek": ("\u0370", "\u03ff"),
    "Arab": ("\u0600", "\u06ff"), "Hebr": ("\u0590", "\u05ff"),
    "Deva": ("\u0900", "\u097f"), "Armn": ("\u0530", "\u058f"),
    "Geor": ("\u10a0", "\u10ff"),
}


def _in_script(form: str, script: str) -> bool:
    """Whether a form is written in the script its language uses."""
    letters = [c for c in form if c.isalpha()]
    if not letters:
        return False
    expected = _SCRIPT_RANGES.get(script or "Latn")
    if expected is None:                       # Latin and everything unlisted
        return not any(_SCRIPT_RANGES["Cyrl"][0] <= c <= _SCRIPT_RANGES["Cyrl"][1]
                       for c in letters)
    lo, hi = expected
    return sum(lo <= c <= hi for c in letters) >= len(letters) / 2


def _diacritics(form: str) -> int:
    import unicodedata
    return sum(1 for c in unicodedata.normalize("NFD", form)
               if unicodedata.combining(c))


def _usable_word(form: str, english: str) -> bool:
    """Reject what a translation table offers that is not a word of the language.

    Three kinds of junk reach a closed-class slot and each produced a visible
    defect: an **affix** (Finnish gives ``-lla`` for *at*, since it has a case
    rather than a preposition, and it was being printed as a separate token), a
    **phrase** (*un certo*, *az ember*), and an **untranslated leak** — the
    English word echoed back, which is how *a cube jaune* happened.
    """
    if not form or form == english:
        return False
    if form.startswith("-") or form.endswith("-") or " " in form:
        return False
    return len(form) <= 14 and not (len(form) == 1 and form.isupper())


CLOSED_CLASS_KEYS: Mapping[str, str] = {
    "the": "the", "a": "a", "not": "not", "and": "and", "or": "or",
    "of": "of", "if": "if", "then": "then", "to": "to", "at": "at",
    "what": "what", "which": "which", "who": "who", "where": "where",
    "when": "when", "why": "why", "how": "how",
    "all": "all", "some": "some", "none": "none", "most": "most",
    "every": "every", "no_quant": "no",
    "few": "few", "empty": "empty",
    "yes": "yes", "no": "no",
    # NOT "a". English "a" is, to a dictionary, the letter A and the musical
    # note, and its translation table is full of both — German came out with
    # *A* and *den*. The indefinite article is historically the numeral in most
    # languages that have one, which is what WALS 38A code 2 records, so "one"
    # is the key that actually retrieves *ein*, *un*, *uno*, *een*, *bir*.
    "a": "one",
    "step": "step", "round": "round", "case": "case", "block": "block",
    "trial": "trial", "turn": "turn", "stage": "stage",
    "is": "be", "are": "be",
}

#: Slots whose English key must be looked up as a **noun**. An ordinal row label
#: — *step 4*, *round 2*, *trial 7* — is a noun in that use, and the untyped
#: lookup returns whichever sense the dictionary lists first: German *round*
#: gives ``rund`` "circular" and *turn* gives a verb. Saying which part of
#: speech is wanted is the whole fix.
NOMINAL_SLOTS = frozenset({"step", "round", "case", "block", "trial", "turn",
                           "stage"})


class DerivedGrammar(Grammar):
    """A grammar for one language, assembled from the language database."""

    def __init__(self, db: LanguageDB, code: str):
        super().__init__()
        self.db = db
        self.code = code
        row = db.language(code)
        self.name = (row["name"] if row else code) or code
        self.tier = row["tier"] if row else 4
        self._params = db.profile(code)
        self._apply_profile(self._params)
        self._word_cache: dict[tuple[str, str], str] = {}
        self._copula: dict[bool, str] = {}
        self._warm_closed_class()
        self._build_articles()
        for category, pos in ((N, "N"), (A, "A"), (V, "V")):
            self.morphology[category.name] = DataMorphology(db, code, pos)
        self.notes = self._notes()

    # ---- parameters ------------------------------------------------------
    def _apply_profile(self, p: Mapping[str, Any]) -> None:
        self.order = WordOrder(
            clause=p.get("clause", "SVO"), adj=p.get("adj", "AN"),
            det=p.get("det", "DN"), numeral=p.get("numeral", "NumN"),
            adposition=p.get("adposition", "pre"),
            possessive=p.get("possessive", "GN"),
            label=p.get("label", "LV"),
            conditional=p.get("conditional", "CA"),
            wh_fronting=bool(p.get("wh_fronting", True)),
            copula_overt=bool(p.get("copula_overt", True)),
            numeral_forces_plural=bool(p.get("numeral_forces_plural", True)),
            negation=p.get("negation", "pre"),
        )
        self.alignment = Alignment(
            case_of=_ALIGNMENTS.get(p.get("alignment", "NO_CASE"), NO_CASE))
        shared = tuple(p.get("concord_adjective") or ())
        if not shared and self._lexicon_records_gender(p):
            shared = (CLS, NUM)
        self.concord = Concord(
            adjective=shared,
            predicative=tuple(p.get("concord_predicative") or ()) or shared)
        self.typography = Typography(
            word_joiner=p.get("word_joiner", " "),
            capitalizes=bool(p.get("capitalizes", True)),
            rtl=bool(p.get("rtl", False)),
            label_separator=":" if not p.get("word_joiner", " ") else "",
        )

    def _lexicon_records_gender(self, p: Mapping[str, Any]) -> bool:
        """Whether the dictionary says this language has gender when WALS did not.

        WALS 30A is **absent** for Italian, Portuguese, Romanian, Polish and
        Czech — not coded zero, simply not coded — and reading a missing value
        as "no genders" switched concord off for five major languages that
        plainly have it. The lexicon settles it: tens of thousands of their
        nouns carry a masculine or feminine tag, which no genderless language's
        entries would. An absent feature is a question, and this answers it from
        evidence rather than from the default.
        """
        if "30A" in (p.get("evidence") or {}):
            return False                       # WALS did code it; believe WALS
        n = self.db.conn.execute(
            "SELECT COUNT(*) FROM sense WHERE code=? AND pos='N' "
            "AND gender IN ('masculine','feminine','neuter')",
            (self.code,)).fetchone()[0]
        return n >= 100

    def _warm_closed_class(self) -> None:
        """One bulk query for the whole closed class, at construction."""
        found = self.db.bulk_lookup(self.code, list(set(CLOSED_CLASS_KEYS.values())))
        for slot, english in CLOSED_CLASS_KEYS.items():
            if slot in NOMINAL_SLOTS:
                entry = self.db.lookup(self.code, english, "N")
            else:
                entry = found.get(english)
            if entry is not None and _usable_word(entry.form, english):
                self.closed[slot] = entry.form
        # a language WALS says has no article must not acquire one from a
        # dictionary that happily translates "the" into a demonstrative
        if not self._params.get("has_definite", False):
            self.closed["the"] = ""
        if not self._params.get("has_indefinite", False):
            self.closed["a"] = ""
        elif self._params.get("indefinite_from_one"):
            self.closed["a"] = self._indefinite_article()
        else:
            # WALS 38A says the indefinite word is distinct from the numeral,
            # and nothing here knows which word it is. The numeral would be the
            # wrong one — Japanese 一つ is "one thing", not an article.
            self.closed["a"] = ""
        if not self.order.copula_overt:
            self.closed["is"] = self.closed["are"] = ""

    # ---- lexicon ---------------------------------------------------------
    def word(self, lemma: str, pos: str = "") -> str:
        key = (lemma, pos)
        hit = self._word_cache.get(key)
        if hit is not None:
            return hit
        entry = self.db.lookup(self.code, lemma, pos)
        form = entry.form if entry is not None else ""
        # A translation table sometimes answers with a gloss rather than a word
        # — English *turn* came back as "be one's turn". A multi-word answer to
        # a *single-word* question is an explanation, not a lexeme. The test is
        # applied here, to what the dictionary said, and not below: a phrase
        # composed token by token is legitimately several words, and screening
        # it by the same rule threw away every translation it produced.
        if " " not in lemma and form and (form.count(" ") > 1 or "'" in form):
            form = ""
        if not form and " " in lemma:
            form = self._phrase(lemma, pos)
        out = form or lemma
        self._word_cache[key] = out
        return out

    def _indefinite_article(self) -> str:
        """The reduced numeral, not the impersonal pronoun.

        English *one* has two senses and both are translated: the numeral, and
        the impersonal subject of *one does not simply…*. The second gives Dutch
        ``je``, Romanian ``se``, German ``man`` — all short, so choosing by
        length alone picks them. Restricting to the **primary sense** keeps the
        numeral, and choosing the shortest of those then reduces the numeral to
        the article: *eins* to *ein*, *uno* to *un*.
        """
        rows = self.db.conn.execute(
            "SELECT form FROM sense WHERE code=? AND key='one' AND rank=0 "
            "AND pos='Card'", (self.code,))
        script = (self.db.language(self.code) or {"script": "Latn"})["script"]
        forms = [r["form"] for r in rows
                 if _usable_word(r["form"], "one") and _in_script(r["form"], script)]
        if not forms:
            return ""
        # A one-letter "article" is almost always the *name* of the numeral
        # rather than the article: Catalan lists u beside un. Prefer a real
        # word where there is one, then the shortest, then the form with the
        # fewest diacritics — Dutch writes één only when stressing the numeral,
        # and een unstressed is the article.
        real = [f for f in forms if len(f) > 1] or forms
        return min(real, key=lambda f: (len(f), _diacritics(f)))

    # ---- the article, from the dictionary's own gender tags ---------------
    _GENDERS = {"masculine": "m", "feminine": "f", "neuter": "n",
                "common": "c", "plural": "pl"}

    def _build_articles(self) -> None:
        """Assemble a gendered article paradigm out of the translation table.

        Wiktionary translates *the* into German as three entries — ``der``
        tagged masculine, ``die`` feminine, ``das`` neuter — and into Spanish,
        French, Italian and Portuguese the same way. So the paradigm that makes
        the difference between *der Buch* and *das Buch* is already in the data,
        and needs reading rather than authoring.
        """
        self._articles: dict[tuple[str, str, bool], str] = {}
        for slot, key in (("def", "the"), ("indef", "one")):
            if not self._params.get(f"has_{'definite' if slot == 'def' else 'indefinite'}"):
                continue
            best: dict[tuple[str, str, bool], str] = {}
            candidates = [e for e in self.db.lookup_all(self.code, key)
                          if key != "one" or e.pos in ("Card", "Det", "A", "")]
            for entry in candidates:
                gender = self._GENDERS.get(entry.gender or "", "")
                if not gender or not _usable_word(entry.form, key):
                    continue
                slots = ([(slot, "m", True), (slot, "f", True)] if gender == "pl"
                         else [(slot, gender, False)])
                for cell in slots:
                    # Shortest wins, as for the copula and for the same reason.
                    # An article is a worn-down numeral and the numeral is still
                    # in the table beside it: German lists *eins* as well as
                    # *ein*, Italian *uno* as well as *un*. The article is the
                    # reduced form, which is to say the shorter one.
                    if cell not in best or len(entry.form) < len(best[cell]):
                        best[cell] = entry.form
            self._articles.update(best)

    def determiner(self, kind: str, head: Node | None, feats: FS) -> str:
        """The gendered article where the data supports one, else the bare word."""
        if kind not in ("def", "indef"):
            return ""
        gender = feats.get_atom(CLS, "") or ""
        plural = feats.get_atom(NUM) == "pl"
        if gender:
            hit = (self._articles.get((kind, gender, plural))
                   or self._articles.get((kind, gender, False)))
            if hit:
                return hit
        return self.cw("the" if kind == "def" else "a")

    def _phrase(self, lemma: str, pos: str) -> str:
        """Translate a multi-word label a token at a time.

        Labels like *value of* and *symbol at position* are built by the
        compiler from a predicate head, and no dictionary has an entry for the
        phrase, so the whole thing passed through in English. Each token does
        have an entry, and translating them separately is a literal rendering
        rather than an idiomatic one — but a literal rendering in the right
        language beats a fluent one in the wrong language.

        Returns nothing unless at least one token actually translated, so a
        phrase made of words the language does not know stays intact rather
        than being half-converted.
        """
        out, translated = [], False
        for token in lemma.split():
            closed = self.cw(token)
            hit = closed or self.word(token, pos=pos if token == lemma else "")
            if hit and hit != token:
                translated = True
            out.append(hit or token)
        return " ".join(out) if translated else ""

    def copula(self, kind: str, feats: FS) -> str:
        """The finite copula, inflected, rather than the dictionary's infinitive.

        Looking up "be" gives a citation form — *sein*, *être*, *ser*, *olmak* —
        and putting an infinitive where a finite verb belongs is the single most
        conspicuous thing a derived grammar can get wrong. UniMorph has the
        third-person singular present for every language it covers, so the
        paradigm answers instead of the headword.
        """
        if not self.order.copula_overt:
            return ""
        plural = feats.get_atom(NUM) == "pl"
        cached = self._copula.get(plural)
        if cached is not None:
            return cached
        lemma = self._copula_lemma()
        want = FS({"pers": "3", NUM: "pl" if plural else "sg",
                   "tense": "pres", "mood": "ind"})
        morph = self.morphology.get(V.name)
        # Attested cells only. The copula is suppletive in most of the world's
        # languages — *is* is not *be* plus a suffix — so the analogical
        # inflector, which learns edge transformations, produces confident
        # nonsense on exactly this verb. Where UniMorph has no paradigm for it
        # the citation form stands: a real word in the wrong cell beats an
        # invented one.
        form = morph._attested(lemma, want) if morph is not None else None
        self._copula[plural] = form or lemma
        return self._copula[plural]

    def _copula_lemma(self) -> str:
        """Pick the copula among the candidates the dictionary offers.

        Wiktionary lists several verbs under *be* — German *werden* as well as
        *sein*, Greek *ίσον* as well as *είμαι*, Turkish *imek* as well as
        *olmak* — and the first is often the wrong one. The tie-break is
        evidence rather than a guess: the copula is the most-inflected verb in
        almost every language that has one, so the candidate with the largest
        attested paradigm is overwhelmingly the right answer. Where no candidate
        is attested at all, the first stands, and the gap is reported by
        :meth:`gaps`.
        """
        candidates = [e.form for e in self.db.lookup_all(self.code, "be")
                      if e.pos in ("V", "")]
        if not candidates:
            return self.word("be", pos="V")
        # mood is safe to request now that a cell is rejected only where it
        # *disagrees*: an untagged cell still matches, and one tagged
        # conditional no longer does
        want = FS({"pers": "3", NUM: "sg", "tense": "pres", "mood": "ind"})
        morph = self.morphology.get(V.name)
        scored: list[tuple[int, int, int, str]] = []
        for position, form in enumerate(dict.fromkeys(candidates[:10])):
            finite = morph._attested(form, want) if morph is not None else None
            # a copula is one word; " lenne or " is a parse artefact, not a verb
            if not finite or " " in finite or len(finite) > 12:
                continue
            scored.append((len(finite), _shared_prefix(form, finite), position, form))
        if scored:
            # Shortest wins, and the dictionary's own sense ranking breaks
            # ties. Length is not an arbitrary proxy: the copula is the most
            # frequent verb in any language that has one, and by Zipf's law the
            # most frequent words are the shortest. Wiktionary lists *werden*
            # beside *sein* and *venire* beside *essere* with nothing to tell
            # them apart, but *ist* is shorter than *wird* and *è* than
            # *viene*. Where two are the same length — Czech *je* beside *má* —
            # suppletion decides: a copula shares almost nothing with its own
            # infinitive (*být*/*je*, *sein*/*ist*, *essere*/*è*) while an
            # ordinary verb keeps its stem (*mít*/*má*). Both are universals
            # about frequency, and between them they pick the right verb in
            # every language checked.
            return min(scored)[3]
        return candidates[0]

    def known(self, lemma: str) -> bool:
        return self.db.lookup(self.code, lemma) is not None

    def features_of(self, lemma: str) -> FS:
        """Inherent features, where the dictionary records them.

        Wiktionary tags a translation with its gender for the languages that
        have one. Where it does not, the noun simply carries no class and the
        concord machinery leaves it alone — which is the correct behaviour for a
        language without gender and an honest one for a gap in the data.
        """
        entry = self.db.lookup(self.code, lemma)
        if entry is None or not entry.gender:
            return EMPTY
        mapped = {"masculine": "m", "feminine": "f", "neuter": "n",
                  "common": "c"}.get(entry.gender, "")
        return FS({CLS: mapped}) if mapped else EMPTY

    def forms(self, lemma: str) -> set[str]:
        surface = self.word(lemma)
        out = {surface, lemma}
        for morph in self.morphology.values():
            out |= morph.forms(surface)
        return {f for f in out if f}

    # ---- section headings -------------------------------------------------
    def block_heading(self, name: str) -> str:
        """``Szene:``, ``escena:``, ``場面:`` — the field name, in the language.

        Not idiomatic: a speaker would write "In der Szene:", and nothing here
        knows how to build that. But a *noun* in the right language is strictly
        better than an English one, and the field names the curriculum uses —
        scene, rules, facts, premises, goal, state — are ordinary words the
        dictionary already has. Translating the head is the honest half of the
        job; the preposition and the article are the half still missing, and
        :meth:`gaps` says so.
        """
        words = name.replace("_", " ")
        translated = self.word(words, pos="N")
        if translated == words:                       # try the bare singular
            translated = self.word(words.rstrip("s"), pos="N")
        return translated + self.typography.colon

    # ---- honesty ---------------------------------------------------------
    def gaps(self) -> list[str]:
        """What this grammar does not know, stated rather than inferred."""
        out: list[str] = []
        p = self._params
        if p.get("order_uncertain"):
            out.append("WALS records no dominant word order; SVO assumed")
        if not p.get("evidence"):
            out.append("no typological coding at all; every parameter is a default")
        if not self.field_intros:
            out.append("section headings are the bare translated noun "
                       "(\u201cSzene:\u201d), not an idiomatic lead-in "
                       "(\u201cIn der Szene:\u201d)")
        row = self.db.language(self.code)
        if row is not None and not row["n_forms"]:
            out.append("no UniMorph data; nouns are not inflected")
        if (self._params.get("has_indefinite")
                and not self._params.get("indefinite_from_one")):
            out.append("WALS records an indefinite word distinct from the "
                       "numeral and nothing here knows which word it is, so "
                       "no indefinite article is emitted")
        if not self._articles and self._params.get("has_definite"):
            out.append("the dictionary records no gender on this language's "
                       "article, so it does not agree with the noun")
        lemma = self._copula_lemma()
        if self.order.copula_overt and not self.db.paradigm(self.code, lemma):
            out.append(f"no attested paradigm for the copula {lemma!r}; "
                       f"the citation form is used")
        if row is not None and row["n_senses"] < 500:
            out.append(f"small lexicon ({row['n_senses']} senses); "
                       f"unknown words pass through in English")
        return out

    def _notes(self) -> tuple[str, ...]:
        p = self._params
        coded = len(p.get("evidence") or {})
        notes = [
            f"derived grammar (tier {self.tier}), not hand-verified",
            f"{self.order.clause}, adjective {self.order.adj}, "
            f"{self.order.adposition}positional, "
            f"{'wh-fronting' if self.order.wh_fronting else 'wh in situ'}",
            f"{coded} WALS/Grambank features coded",
        ]
        if self.concord.adjective:
            notes.append(f"noun class concord over {p.get('n_classes')} classes")
        if p.get("classifiers") != "absent":
            notes.append(f"numeral classifiers {p.get('classifiers')}")
        notes.append("NOT attempted: " + "; ".join(self.gaps())
                     if self.gaps() else "NOT attempted: idiomatic phrasing")
        return tuple(notes)

    def info(self) -> dict[str, Any]:
        base = super().info()
        row = self.db.language(self.code)
        base.update({
            "tier": self.tier,
            "senses": row["n_forms"] if row else 0,
            "n_senses": row["n_senses"] if row else 0,
            "n_forms": row["n_forms"] if row else 0,
            "typology_features": len(self._params.get("evidence") or {}),
            "gaps": self.gaps(),
        })
        return base
