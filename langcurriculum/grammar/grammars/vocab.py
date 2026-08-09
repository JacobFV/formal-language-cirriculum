"""Wiring the existing typed vocabularies into the grammar engine.

The three shipped packs already carry 321 typed open-class entries each, loaded
from JSON, with the gender, plural, classifier and agreement forms their
languages need. None of that work is invalidated by moving to a grammar — it is
exactly the lexicon a grammar wants — so this module adapts it rather than
replacing it.

The adaptation is one idea: a vocabulary entry's stored fields become
**inherent features** on the lemma. A Spanish noun's ``gender`` becomes
``FS(cls="f")``; a Chinese noun's ``classifier`` becomes ``FS(clf="本")``; a
Swahili noun's class becomes ``FS(cls="7")``. From there the concord machinery
in :mod:`~langcurriculum.grammar.linearize` handles all three identically,
which is the whole argument of the rewrite in one function.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ...languages.lexicon import Vocabulary, load_vocabulary
from ..category import CLF, CLS
from ..features import FS
from ..linearize import Grammar

__all__ = ["VocabularyGrammar", "load_pack"]

_LOCAL_DATA = Path(__file__).resolve().parent / "data"

#: distinguishes "not looked up yet" from "looked up and absent"
_UNSET = object()


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Overlay a data file onto a pack, merging tables rather than replacing them.

    A plain ``{**base, **overlay}`` replaces whole keys, and the packs keep large
    tables under exactly the keys an overlay wants to extend: Spanish ships 475
    relational phrasings and the overlay adds 35, so replacing dropped 440 of
    them silently. Dictionaries merge with the overlay winning per key;
    everything else is replaced, which is what a scalar or a list should do.
    """
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **value}
        else:
            out[key] = value
    return out


def load_pack(code: str) -> tuple[Vocabulary, dict[str, Any]]:
    """Load a vocabulary from ``languages/data`` or ``grammar/grammars/data``.

    New languages ship their data beside their grammar; the three original packs
    keep theirs where they already are, so nothing has to move.
    """
    try:
        return load_vocabulary(code)
    except FileNotFoundError:
        path = _LOCAL_DATA / f"{code}.json"
        if not path.exists():
            raise
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _vocabulary_from(raw), raw


def _vocabulary_from(raw: Mapping[str, Any]) -> Vocabulary:
    """Build a :class:`Vocabulary` from a raw JSON pack.

    Deliberately the same shape as the loader in ``languages/lexicon.py``, minus
    the caching, so a new language's data file looks like an old one's and a
    reader comparing them finds no surprises.
    """
    from ...languages.lexicon import Adjective, Noun, Verb
    return Vocabulary(
        nouns={k: Noun(lemma=v["lemma"], gender=v.get("gender", ""),
                       plural=v.get("plural", ""), classifier=v.get("classifier", ""))
               for k, v in (raw.get("nouns") or {}).items()},
        adjectives={k: Adjective(base=v.get("base") or v.get("ms") or v.get("form", ""),
                                 ms=v.get("ms", ""), fs=v.get("fs", ""),
                                 mp=v.get("mp", ""), fp=v.get("fp", ""),
                                 linker=bool(v.get("attributive_de", False)))
                    for k, v in (raw.get("adjectives") or {}).items()},
        verbs={k: Verb(base=v.get("base") or v.get("form") or v.get("inf") or v.get("s3", ""),
                       infinitive=v.get("inf", ""), s3=v.get("s3", ""),
                       p3=v.get("p3", ""), past3=v.get("past3", ""),
                       aspect=v.get("aspect", ""))
               for k, v in (raw.get("verbs") or {}).items()},
        names=dict(raw.get("names") or {}),
        words=dict(raw.get("words") or {}),
    )


class VocabularyGrammar(Grammar):
    """A grammar backed by one of the typed JSON vocabularies.

    The curated vocabulary is small and verified; the language database is large
    and scraped. Both are useful and the order between them is the whole point:
    **curated wins, and the database fills the gaps.** Turkish ships 115 of the
    curriculum's 403 keys by hand and the database has 224 of them, so consulting
    it roughly doubles what a hand-written grammar can say without touching a
    single one of its verified entries.
    """

    #: which data file to load; defaults to the grammar's code
    pack: str = ""

    #: ISO 639-3 code, for reaching the language database. Empty means the
    #: grammar is curated-only — English, whose database rows would be
    #: English-to-English and therefore empty anyway.
    iso: str = ""

    #: an extra data file merged over the pack's own, for material that used to
    #: live in the template module: English's field lead-ins and synonyms
    overlay: str = ""

    def __init__(self) -> None:
        super().__init__()
        self._database: Any = _UNSET
        self.vocabulary, self.raw = load_pack(self.pack or self.code)
        if self.overlay:
            extra_path = _LOCAL_DATA / f"{self.overlay}.json"
            if extra_path.exists():
                self.raw = _merge(
                    self.raw, json.loads(extra_path.read_text(encoding="utf-8")))
        self.predicate_words = dict(self.raw.get("predicate_words") or {})
        self.field_intros = dict(self.raw.get("field_intros") or {})
        self.closed = dict(self.raw.get("closed") or {})
        self.paradigms = {k: ([tuple(x) if isinstance(x, list) else x for x in v]
                              if isinstance(v, list) else v)
                          for k, v in (self.raw.get("paradigms") or {}).items()}
        self._build_inherent()
        self._import_gaps()

    def _build_inherent(self) -> None:
        """Turn stored lexical fields into inherent features on the lemma."""
        for key, noun in self.vocabulary.nouns.items():
            feats: dict[str, Any] = {}
            if noun.gender:
                feats[CLS] = noun.gender
            if noun.classifier:
                feats[CLF] = noun.classifier
            cls = (self.raw.get("noun_class") or {}).get(key)
            if cls:
                feats[CLS] = str(cls)
            if feats:
                self.inherent[key] = FS(feats)

    # ---- lexical access -------------------------------------------------
    def _import_gaps(self) -> None:
        """Fill the curated vocabulary's gaps from the database, unambiguously.

        Two rules, and both are about not breaking the episode.

        **Only curriculum vocabulary.** A coined identifier must never be
        translated — the lesson turns on it — and some are short enough to
        collide with a real word: Spanish rendered the nonce ``nu`` as ``ni``,
        which is also what the nonce ``ni`` rendered as. Restricting the import
        to keys the curriculum actually coins means a minted token is never
        looked up at all.

        **No collisions.** A dictionary will happily give one word for two
        concepts — Turkish *para* is both *money* and *coin*, Swahili *sanduku*
        both *crate* and *box* — and an episode naming both becomes
        unanswerable. Where an imported form would collide, with another import
        or with a curated entry, it is dropped and the English passes through.
        A visibly untranslated word is a much smaller problem than an ambiguous
        one, which is the same trade the curated packs were built on.
        """
        self._imported: dict[str, str] = {}
        db = self.database
        if db is None:
            return
        from ..compile import curriculum_vocabulary

        taken = {self.vocabulary.translate(k) for k in
                 (set(self.vocabulary.nouns) | set(self.vocabulary.adjectives)
                  | set(self.vocabulary.verbs) | set(self.vocabulary.words)
                  | set(self.vocabulary.names))}
        taken |= set(self.predicate_words.values())
        candidates: dict[str, str] = {}
        for key in sorted(curriculum_vocabulary()):
            if self.vocabulary.knows(key) or key in self.predicate_words:
                continue
            entry = db.lookup(self.iso, key)
            if entry is None or not entry.form:
                continue
            form = entry.form
            # the screen the derived grammars apply: a table sometimes answers a
            # one-word question with an explanation rather than a word
            if form.count(" ") > 1 or "'" in form or form == key:
                continue
            candidates[key] = form

        seen: dict[str, str] = {}
        for key, form in candidates.items():
            if form in taken or form in seen:
                seen.pop(form, None)          # drop both sides of a collision
                continue
            seen[form] = key
        self._imported = {k: f for f, k in seen.items()}

    @property
    def database(self):
        """The language database, or ``None`` where it has not been built.

        Looked up lazily and cached: a grammar must stay usable with no database
        at all, since the hand-written five are the ones that work out of the box.
        """
        if self._database is _UNSET:
            self._database = None
            if self.iso:
                from ..store import LanguageDB
                db = LanguageDB()
                self._database = db if db.exists() else None
        return self._database

    def lookup(self, lemma: str, pos: str = "") -> str:
        """The open-class word, then the relational lexicon, then the database.

        ``predicate_words`` is consulted second because it is exactly a lexicon
        of relational predicates — 475 entries per pack, already authored — and a
        relational verb reaching this point is precisely what it is for. The
        lemma passing through unchanged is the last resort and the commonest
        outcome, because most of what this curriculum names is coined per
        episode.
        """
        relational = self.predicate_words.get(lemma)
        if pos == "V" and relational:
            return relational
        if self.vocabulary.knows(lemma):
            surface = self.vocabulary.translate(lemma)
            # A vocabulary entry that maps a word to itself is not a
            # translation — several are present only so the word is recognised.
            # Letting one shadow the relational lexicon is how ``left_of`` comes
            # out as "left_of" instead of "to the left of".
            if surface != lemma:
                return surface
        if relational:
            return relational
        return self._imported.get(lemma, "")

    def known(self, lemma: str) -> bool:
        return self.vocabulary.knows(lemma)

    def forms(self, lemma: str) -> set[str]:
        """Every surface form this grammar could produce for one source word.

        Union of what the vocabulary stores and what the morphology derives —
        the latter matters for agglutinative languages, where the stored form is
        one cell of a paradigm with hundreds.
        """
        out = set(self.vocabulary.forms(lemma))
        surface = self.word(lemma)
        for morph in self.morphology.values():
            out |= morph.forms(surface)
        return {f for f in out if f}

    def info(self) -> dict[str, Any]:
        base = super().info()
        base["vocabulary"] = self.vocabulary.counts()
        return base
