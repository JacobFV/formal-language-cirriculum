#!/usr/bin/env python3
"""Harvest inflection tables from per-language Wiktionary extracts.

UniMorph is the better source for regular open-class morphology and it is what
:mod:`langcurriculum.grammar.induce` learns from. It has one systematic gap, and
it is exactly the gap that hurts: **suppletive auxiliaries are missing**. German
``ist``, Russian ``есть``, Polish ``jest`` and Italian ``è`` do not appear in
their languages' UniMorph files at all, though each of those files runs to
hundreds of thousands of forms. UniMorph is a paradigm resource, and the copula
does not have a paradigm so much as a list.

The consequence was visible in every derived grammar: with no attested cell for
the copula, the linearizer fell back to the citation form and German attributive
clauses read *das Buch sein* — or, once candidate ranking was added, picked
whichever verb under English *be* did have forms, and said *wird*.

Wiktionary has the list. The entry for ``sein`` carries 113 forms, each tagged:
``ist`` is ``['present', 'singular', 'third-person']``. This script reads those
tables for a set of languages and writes them into the same ``wordform`` table
UniMorph populates, under the source ``wiktionary``, so the inducer and the
attested-cell lookup both see them without changing.

    python scripts/load_wiktionary_forms.py --raw <dir> --db <path>

Source: Wiktextract / kaikki.org (Tatu Ylonen, 2022), from English Wiktionary,
CC-BY-SA. Per-language extracts, one file per language.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: Wiktionary's tag vocabulary, mapped onto UniMorph's. The bundle is stored in
#: UniMorph notation so that one parser serves both sources and the inducer
#: never has to know where a cell came from.
TAG_TO_UM = {
    "singular": "SG", "plural": "PL", "dual": "DU",
    "first-person": "1", "second-person": "2", "third-person": "3",
    "present": "PRS", "past": "PST", "future": "FUT",
    "indicative": "IND", "subjunctive": "SBJV", "imperative": "IMP",
    "conditional": "COND", "infinitive": "NFIN",
    "nominative": "NOM", "accusative": "ACC", "genitive": "GEN",
    "dative": "DAT", "ablative": "ABL", "locative": "LOC",
    "instrumental": "INS", "vocative": "VOC", "partitive": "PRT",
    "inessive": "IN+ESS", "elative": "ABL", "illative": "IN+ALL",
    "adessive": "AT+ESS", "essive": "ESS", "translative": "TRANS",
    "ergative": "ERG", "absolutive": "ABS", "comitative": "COM",
    "masculine": "MASC", "feminine": "FEM", "neuter": "NEUT",
    "definite": "DEF", "indefinite": "INDF",
    "positive": "POS", "negative": "NEG",
    "participle": "V.PTCP", "gerund": "V.MSDR",
}

#: Rows carrying any of these are table scaffolding, not word forms. Wiktextract
#: emits them alongside the real cells and storing them would pollute both the
#: attested lookup and the statistics the inducer computes.
SKIP_TAGS = frozenset({
    "table-tags", "inflection-template", "class", "error-unrecognized-form",
    "romanization", "transliteration", "obsolete", "archaic", "dialectal",
    "rare", "nonstandard", "misspelling", "alternative", "no-table-tags",
})

POS_TO_UM = {"verb": "V", "noun": "N", "adj": "A", "adv": "ADV",
             "det": "DET", "pron": "PRO", "num": "NUM"}


def harvest(path: Path, code: str, conn: sqlite3.Connection, *,
            max_forms_per_entry: int = 200) -> int:
    """Read one language's extract and write its inflection tables."""
    batch: list[tuple[str, str, str, str, str, str]] = []
    written = 0
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            lemma = entry.get("word") or ""
            pos = POS_TO_UM.get(entry.get("pos") or "", "")
            forms = entry.get("forms") or []
            if not lemma or not pos or not forms:
                continue
            for f in forms[:max_forms_per_entry]:
                surface = (f.get("form") or "").strip()
                tags = f.get("tags") or []
                # A "form" with a space in it is a phrase, not an inflected
                # word: Wiktextract emits periphrastic cells (Czech "byla by")
                # and parse artefacts ("lenne or") alongside the real ones. The
                # engine inflects words, so a phrase in a paradigm cell is
                # noise that corrupts both attested lookup and induction.
                if (not surface or surface == lemma or len(surface) > 40
                        or " " in surface or "/" in surface):
                    continue
                if any(t in SKIP_TAGS for t in tags):
                    continue
                mapped = [TAG_TO_UM[t] for t in tags if t in TAG_TO_UM]
                if not mapped:
                    continue
                bundle = ";".join([pos, *dict.fromkeys(mapped)])
                batch.append((code, lemma, surface, bundle, pos, "wiktionary"))
            if len(batch) >= 100_000:
                conn.executemany(
                    "INSERT INTO wordform (code,lemma,surface,feats,pos,source) "
                    "VALUES (?,?,?,?,?,?)", batch)
                conn.commit()
                written += len(batch)
                batch.clear()
    if batch:
        conn.executemany(
            "INSERT INTO wordform (code,lemma,surface,feats,pos,source) "
            "VALUES (?,?,?,?,?,?)", batch)
        conn.commit()
        written += len(batch)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True,
                    help="the same directory build_langdb.py reads; the "
                         "extracts are taken from its wikt/ subdirectory")
    ap.add_argument("--db", required=True, help="the language database to add to")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA synchronous = OFF")
    totals: Counter = Counter()
    # `--raw` means the same thing here as it does to build_langdb.py: the
    # directory holding every source. It used to mean the subdirectory with the
    # extracts in it, so passing the same path to both scripts -- which is what
    # the README tells you to do -- silently loaded nothing and printed
    # "total: 0 forms across 0 languages" at the end of a long build.
    raw = Path(args.raw)
    source = raw / "wikt" if (raw / "wikt").is_dir() else raw
    for path in sorted(source.glob("*.jsonl.gz")):
        code = path.name.split(".")[0]
        if len(code) != 3:
            continue
        n = harvest(path, code, conn)
        totals[code] = n
        print(f"  {code}: {n:,} forms", file=sys.stderr)

    # the counts the tier assignment reads have to be refreshed
    conn.execute(
        "UPDATE language SET n_forms = ("
        "  SELECT COUNT(*) FROM wordform w WHERE w.code = language.code)")
    conn.execute("UPDATE language SET tier=2 "
                 "WHERE n_forms >= 1000 AND n_senses >= 200")
    conn.commit()
    conn.close()
    print(f"total: {sum(totals.values()):,} forms across {len(totals)} languages",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
