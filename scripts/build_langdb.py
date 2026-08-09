#!/usr/bin/env python3
"""Build the language database from public linguistic datasets.

Everything the grammar engine knows about a language beyond its hand-written
grammar comes from here, and every row it writes records where it came from.
Three sources, all openly licensed, all cited:

**WALS** — *The World Atlas of Language Structures Online* (Dryer & Haspelmath,
eds., 2013), CLDF release, CC-BY 4.0. Typological coding for 2,660 languages.
This is what supplies word order, alignment, article inventory and concord;
see :mod:`langcurriculum.grammar.typology` for the feature-by-feature mapping.

**Grambank** (Skirgård et al. 2023), CC-BY 4.0. A second, denser typological
coding, used where WALS has a gap.

**UniMorph** (Batsuren et al., UniMorph 4.0), CC-BY-SA. Inflected forms with
morphological feature bundles — 16.4 million of them across 174 languages. This
is what makes morphology *derived* rather than stored: a Finnish noun's hundred
and forty cells are data, not a table someone typed.

**Wiktextract / kaikki.org** (Tatu Ylonen, 2022), from English Wiktionary,
CC-BY-SA. Translation tables: the English lemma the curriculum coins, and what
it is in each target language.

    python scripts/build_langdb.py --raw <dir>          # build from a download
    python scripts/build_langdb.py --raw <dir> --fetch  # download first

Nothing here runs at import time and nothing here is required to *use* the
package with its hand-written grammars. It is required to use the hundred
derived ones.
"""

from __future__ import annotations

import argparse
import os
import csv
import gzip
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langcurriculum.grammar.store import INDEXES, SCHEMA, open_db   # noqa: E402
from langcurriculum.grammar.typology import (                       # noqa: E402
    WALS_FEATURES, derive_profile,
)

csv.field_size_limit(10_000_000)

# ----------------------------------------------------------------------
# source URLs, kept here so the provenance is readable next to the loader
# ----------------------------------------------------------------------
WALS_BASE = "https://raw.githubusercontent.com/cldf-datasets/wals/master/cldf"
GRAMBANK_BASE = "https://raw.githubusercontent.com/grambank/grambank/master/cldf"
UNIMORPH_BASE = "https://raw.githubusercontent.com/unimorph"
KAIKKI_EN = ("https://kaikki.org/dictionary/English/"
             "kaikki.org-dictionary-English.jsonl.gz")

#: UniMorph part-of-speech tags mapped onto the engine's categories
UM_POS = {"N": "N", "V": "V", "ADJ": "A", "ADV": "Adv", "PRO": "Pron",
          "DET": "Det", "NUM": "Card", "ADP": "P", "CONJ": "Conj"}

#: Wiktionary part-of-speech names mapped onto the engine's categories
WIKT_POS = {"noun": "N", "verb": "V", "adj": "A", "adv": "Adv",
            "num": "Card", "prep": "P", "conj": "Conj", "det": "Det"}


# ======================================================================
# fetching
# ======================================================================
def fetch_all(raw: Path) -> None:
    """Download every source. Skips anything already present."""
    import urllib.request

    def get(url: str, dest: Path) -> None:
        if dest.exists() and dest.stat().st_size > 0:
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"  fetching {url}", file=sys.stderr)
        urllib.request.urlretrieve(url, dest)

    for name in ("languages", "values", "parameters", "codes"):
        get(f"{WALS_BASE}/{name}.csv", raw / "typology" / f"wals-{name}.csv")
    for name in ("languages", "values", "parameters"):
        get(f"{GRAMBANK_BASE}/{name}.csv", raw / "typology" / f"grambank-{name}.csv")
    get(KAIKKI_EN, raw / "kaikki-en.jsonl.gz")
    print("  UniMorph: run scripts/fetch_unimorph.py --raw <dir> (170 repositories)",
          file=sys.stderr)


# ======================================================================
# typology
# ======================================================================
def load_typology(conn: sqlite3.Connection, raw: Path) -> dict[str, dict[str, str]]:
    """WALS and Grambank into the ``typology`` table, keyed by ISO 639-3."""
    tdir = raw / "typology"
    langs: dict[str, dict[str, Any]] = {}
    wals_id_to_iso: dict[str, str] = {}

    for row in csv.DictReader(open(tdir / "wals-languages.csv", encoding="utf-8")):
        iso = (row.get("ISO639P3code") or "").strip()
        if not iso:
            continue
        wals_id_to_iso[row["ID"]] = iso
        langs.setdefault(iso, {
            "code": iso, "name": row["Name"],
            "glottocode": row.get("Glottocode") or "",
            "family": row.get("Family") or "",
            "macroarea": row.get("Macroarea") or "",
        })

    coding: dict[str, dict[str, str]] = defaultdict(dict)
    rows: list[tuple[str, str, str, str]] = []
    for v in csv.DictReader(open(tdir / "wals-values.csv", encoding="utf-8")):
        iso = wals_id_to_iso.get(v["Language_ID"])
        if not iso or v["Parameter_ID"] not in WALS_FEATURES:
            continue
        coding[iso][v["Parameter_ID"]] = v["Value"]
        rows.append((iso, v["Parameter_ID"], v["Value"], "wals"))

    # Grambank fills gaps and adds languages WALS never coded
    gb_id_to_iso: dict[str, str] = {}
    gfile = tdir / "grambank-languages.csv"
    if gfile.exists():
        for row in csv.DictReader(open(gfile, encoding="utf-8")):
            iso = (row.get("ISO639P3code") or "").strip()
            if not iso:
                continue
            gb_id_to_iso[row["ID"]] = iso
            langs.setdefault(iso, {
                "code": iso, "name": row["Name"],
                "glottocode": row.get("Glottocode") or "",
                "family": row.get("Family_name") or "",
                "macroarea": row.get("Macroarea") or "",
            })
        for v in csv.DictReader(open(tdir / "grambank-values.csv", encoding="utf-8")):
            iso = gb_id_to_iso.get(v["Language_ID"])
            if not iso or not v.get("Value"):
                continue
            rows.append((iso, v["Parameter_ID"], v["Value"], "grambank"))

    conn.executemany(
        "INSERT OR REPLACE INTO typology (code,param,value,source) VALUES (?,?,?,?)",
        rows)
    conn.executemany(
        "INSERT OR IGNORE INTO language (code,name,glottocode,family,macroarea) "
        "VALUES (:code,:name,:glottocode,:family,:macroarea)", list(langs.values()))
    conn.commit()
    print(f"  typology: {len(langs)} languages, {len(rows)} coded values",
          file=sys.stderr)
    return coding


# ======================================================================
# morphology
# ======================================================================
def load_unimorph(conn: sqlite3.Connection, raw: Path) -> Counter:
    """Every UniMorph paradigm file into ``wordform``.

    UniMorph lines are ``lemma \\t inflected \\t FEATS``, where FEATS is a
    semicolon-separated bundle whose first element is the part of speech. The
    bundle is stored verbatim: translating it into engine features is the
    inducer's job, and keeping the raw string means a later, better inducer can
    reread it without a rebuild.
    """
    udir = raw / "unimorph"
    if not udir.exists():
        print("  unimorph: directory absent, skipping", file=sys.stderr)
        return Counter()
    counts: Counter = Counter()
    for path in sorted(udir.glob("*.tsv")):
        code = path.stem
        if len(code) != 3:
            continue
        batch: list[tuple[str, str, str, str, str]] = []
        for line in path.open(encoding="utf-8", errors="replace"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            lemma, surface, feats = parts[0], parts[1], parts[2]
            if not lemma or not surface or not feats:
                continue
            pos = UM_POS.get(feats.split(";")[0], "")
            batch.append((code, lemma, surface, feats, pos))
        if not batch:
            continue
        conn.executemany(
            "INSERT INTO wordform (code,lemma,surface,feats,pos,source) "
            "VALUES (?,?,?,?,?,'unimorph')", batch)
        counts[code] = len(batch)
        conn.commit()
    print(f"  unimorph: {len(counts)} languages, {sum(counts.values()):,} forms",
          file=sys.stderr)
    return counts


# ======================================================================
# lexicon
# ======================================================================
_PAREN = re.compile(r"\s*\([^)]*\)")
_BAD = re.compile(r"[\[\]{}<>|]")


def _clean(word: str) -> str:
    """Strip the annotations Wiktionary translation tables carry inline."""
    word = _PAREN.sub("", word).strip()
    word = word.split(",")[0].strip()
    return "" if _BAD.search(word) else word


def load_wiktionary(conn: sqlite3.Connection, raw: Path, *,
                    keys: set[str] | None = None,
                    max_per_key: int = 3) -> Counter:
    """Translation tables from the Wiktextract dump into ``sense``.

    One pass over a 502 MB gzip. For each English entry the extractor recorded a
    translation table for, every target language becomes a row. ``keys``
    restricts the harvest to a concept list; passing ``None`` takes the lot,
    which is what "no small dictionary" means in practice — the whole of English
    Wiktionary's translation data, for every language it covers.
    """
    path = raw / "kaikki-en.jsonl.gz"
    if not path.exists():
        print("  wiktionary: dump absent, skipping", file=sys.stderr)
        return Counter()
    counts: Counter = Counter()
    seen: Counter = Counter()
    batch: list[tuple[str, str, str, str, str, str]] = []
    n_entries = 0

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = entry.get("word") or ""
            # Wiktionary attaches a translation table to a *sense*, not to the
            # headword, because "bank" translates differently per meaning. Only
            # a small minority of entries carry one at the top level, so reading
            # only that misses roughly nine tenths of the data.
            groups: list[list[dict]] = []
            if entry.get("translations"):
                groups.append(list(entry["translations"]))
            for sn in entry.get("senses") or []:
                if sn.get("translations"):
                    groups.append(list(sn["translations"]))
            # A sense's breadth of translation is a good proxy for how central
            # it is: "big = large" is translated into a hundred languages and
            # "big = grown-up" into a handful. Ranking by it puts the word a
            # reader expects first, in every language at once.
            groups.sort(key=len, reverse=True)
            translations = [(rank, t) for rank, g in enumerate(groups) for t in g]
            if not key or not translations:
                continue
            if keys is not None and key not in keys:
                continue
            n_entries += 1
            pos = WIKT_POS.get(entry.get("pos") or "", "")
            for rank, t in translations:
                code, word = t.get("code"), t.get("word")
                if not code or not word or len(code) < 2:
                    continue
                form = _clean(word)
                if not form:
                    continue
                pair = (code, key, pos)
                if seen[pair] >= max_per_key:
                    continue
                seen[pair] += 1
                batch.append((code, key, pos, form, t.get("tags", [""])[0]
                              if isinstance(t.get("tags"), list) and t.get("tags")
                              else "", rank, "wiktionary"))
                counts[code] += 1
            if len(batch) >= 200_000:
                conn.executemany(
                    "INSERT INTO sense (code,key,pos,form,gender,rank,source) "
                    "VALUES (?,?,?,?,?,?,?)", batch)
                conn.commit()
                batch.clear()
    if batch:
        conn.executemany(
            "INSERT INTO sense (code,key,pos,form,gender,rank,source) "
            "VALUES (?,?,?,?,?,?,?)", batch)
        conn.commit()
    print(f"  wiktionary: {n_entries:,} English entries -> "
          f"{sum(counts.values()):,} senses in {len(counts)} languages",
          file=sys.stderr)
    return counts


# ======================================================================
# assembling
# ======================================================================
#: two- and three-letter codes both appear in the wild; the database keys on
#: ISO 639-3, so the two-letter ones are folded in.
ISO1_TO_ISO3 = {
    "en": "eng", "es": "spa", "zh": "cmn", "tr": "tur", "sw": "swh",
    "de": "deu", "fr": "fra", "ru": "rus", "ja": "jpn", "ko": "kor",
    "ar": "arb", "hi": "hin", "pt": "por", "it": "ita", "nl": "nld",
    "pl": "pol", "fi": "fin", "hu": "hun", "cs": "ces", "sv": "swe",
    "da": "dan", "no": "nob", "el": "ell", "he": "heb", "th": "tha",
    "vi": "vie", "id": "ind", "ms": "msa", "fa": "pes", "uk": "ukr",
    "ro": "ron", "bg": "bul", "hr": "hrv", "sr": "srp", "sk": "slk",
    "sl": "slv", "lt": "lit", "lv": "lav", "et": "est", "is": "isl",
    "ga": "gle", "cy": "cym", "eu": "eus", "ca": "cat", "gl": "glg",
    "hy": "hye", "ka": "kat", "az": "azj", "kk": "kaz", "uz": "uzn",
    "mn": "khk", "ne": "npi", "bn": "ben", "ta": "tam", "te": "tel",
    "ml": "mal", "kn": "kan", "mr": "mar", "gu": "guj", "pa": "pan",
    "si": "sin", "my": "mya", "km": "khm", "lo": "lao", "am": "amh",
    "ti": "tir", "so": "som", "ha": "hau", "yo": "yor", "ig": "ibo",
    "zu": "zul", "xh": "xho", "af": "afr", "sq": "als", "mk": "mkd",
    "be": "bel", "tg": "tgk", "ky": "kir", "tk": "tuk", "ps": "pbu",
    "ku": "kmr", "ur": "urd", "mt": "mlt", "lb": "ltz", "fo": "fao",
    "eo": "epo", "la": "lat", "sa": "san", "yi": "ydd", "tl": "tgl",
    "jv": "jav", "su": "sun", "haw": "haw", "mi": "mri", "sm": "smo",
    "to": "ton", "fj": "fij", "qu": "quz", "ay": "ayr", "gn": "gug",
    "nv": "nav", "iu": "ike", "kl": "kal", "se": "sme", "br": "bre",
}

#: default script per language, for the languages whose typography differs.
#: Everything unlisted is assumed Latin, which is right far more often than not
#: and is corrected per language by a hand-written grammar where it matters.
SCRIPTS = {
    "cmn": "Hans", "yue": "Hant", "jpn": "Jpan", "kor": "Hang",
    "arb": "Arab", "pes": "Arab", "urd": "Arab", "pbu": "Arab", "ckb": "Arab",
    "heb": "Hebr", "ydd": "Hebr", "amh": "Ethi", "tir": "Ethi",
    "rus": "Cyrl", "ukr": "Cyrl", "bul": "Cyrl", "srp": "Cyrl", "mkd": "Cyrl",
    "bel": "Cyrl", "kaz": "Cyrl", "khk": "Cyrl", "tgk": "Cyrl", "kir": "Cyrl",
    "sah": "Cyrl", "tyv": "Cyrl", "chv": "Cyrl", "tat": "Cyrl", "bak": "Cyrl",
    "ell": "Grek", "hye": "Armn", "kat": "Geor",
    "hin": "Deva", "mar": "Deva", "npi": "Deva", "san": "Deva",
    "ben": "Beng", "asm": "Beng", "pan": "Guru", "guj": "Gujr",
    "ory": "Orya", "tam": "Taml", "tel": "Telu", "kan": "Knda",
    "mal": "Mlym", "sin": "Sinh", "tha": "Thai", "lao": "Laoo",
    "mya": "Mymr", "khm": "Khmr", "bod": "Tibt", "dzo": "Tibt",
    "div": "Thaa", "iku": "Cans", "ike": "Cans",
}


def assemble(conn: sqlite3.Connection, coding: dict[str, dict[str, str]]) -> None:
    """Derive a profile per language and tier every language by its real data."""
    counts = {
        "sense": {r[0]: r[1] for r in conn.execute(
            "SELECT code, COUNT(*) FROM sense GROUP BY code")},
        "wordform": {r[0]: r[1] for r in conn.execute(
            "SELECT code, COUNT(*) FROM wordform GROUP BY code")},
        "typology": {r[0]: r[1] for r in conn.execute(
            "SELECT code, COUNT(DISTINCT param) FROM typology GROUP BY code")},
    }
    # fold ISO 639-1 rows (as Wiktionary writes them) into ISO 639-3
    for iso1, iso3 in ISO1_TO_ISO3.items():
        n = conn.execute("SELECT COUNT(*) FROM sense WHERE code=?", (iso1,)).fetchone()[0]
        if n:
            conn.execute("UPDATE sense SET code=? WHERE code=?", (iso3, iso1))
    conn.commit()
    counts["sense"] = {r[0]: r[1] for r in conn.execute(
        "SELECT code, COUNT(*) FROM sense GROUP BY code")}

    profiles: list[tuple[str, str, str]] = []
    updates: list[tuple[int, int, int, int, str, int, str]] = []
    demote: list[str] = []
    all_codes = set(counts["typology"]) | set(counts["sense"]) | set(counts["wordform"])
    for code in sorted(all_codes):
        wals = coding.get(code, {})
        script = SCRIPTS.get(code, "Latn")
        profile = derive_profile(code, wals, script=script)
        n_sense = counts["sense"].get(code, 0)
        n_form = counts["wordform"].get(code, 0)
        n_typ = counts["typology"].get(code, 0)
        # A real lexicon is enough on its own. Esperanto and Galician have no
        # WALS coding — one is constructed, the other is usually folded into
        # Portuguese — yet both translate more than half the curriculum. Dropping
        # them for want of typology would discard real data to satisfy a filter.
        if n_typ < 4 and not n_form and n_sense < 200:
            # too little to claim anything about. Explicitly tier 4 rather than
            # left at whatever the column defaults to: a language nothing was
            # learned about must never inherit a tier that means it was.
            demote.append(code)
            continue
        profiles.append((code, json.dumps(profile.to_json(), ensure_ascii=False),
                         "wals+grambank"))
        # tier 1 is claimed by a hand-written grammar, never derived here
        if n_form >= 1000 and n_sense >= 200:
            tier = 2
        elif n_sense >= 200:
            tier = 3
        else:
            tier = 4
        updates.append((n_sense, n_form, n_typ, tier, script,
                        1 if profile.typography.rtl else 0, code))

    conn.executemany(
        "INSERT OR REPLACE INTO profile (code,params,derived_from) VALUES (?,?,?)",
        profiles)
    conn.executemany(
        "INSERT OR IGNORE INTO language (code,name) VALUES (?,?)",
        [(c, c) for c in all_codes])
    conn.executemany(
        "UPDATE language SET n_senses=?, n_forms=?, n_typology=?, tier=?, "
        "script=?, rtl=? WHERE code=?", updates)
    conn.executemany("UPDATE language SET tier=4 WHERE code=?",
                     [(c,) for c in demote])
    conn.execute("UPDATE language SET tier=4 WHERE n_senses<200 AND n_forms<1000")
    conn.commit()
    print(f"  profiles: {len(profiles)} languages", file=sys.stderr)


def _real_target(out: Path) -> Path:
    """Where the file actually lives, following a symlink if one is in the way.

    The database is large enough that people keep it outside the package and
    link to it, and replacing the *link* with a two-gigabyte regular file
    would quietly undo that arrangement -- and put the file somewhere they had
    deliberately moved it away from. Following the link also keeps the
    temporary file on the same filesystem as its destination, which is what
    makes the final move atomic rather than a copy.
    """
    return out.resolve() if out.is_symlink() else out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True, help="directory holding the downloads")
    ap.add_argument("--out", default=None, help="database path")
    ap.add_argument("--fetch", action="store_true", help="download first")
    ap.add_argument("--all-words", action="store_true",
                    help="harvest every English entry, not just curriculum keys")
    args = ap.parse_args()

    raw = Path(args.raw)
    if args.fetch:
        fetch_all(raw)

    out = Path(args.out) if args.out else (
        ROOT / "langcurriculum" / "grammar" / "data" / "languages.db")
    # Built beside the real one and moved over it at the end. The old code
    # deleted the database first and spent the next several hours filling a
    # new one, so a dropped connection, a parse error or an interrupt left the
    # package with no lexicon at all and nothing to fall back to -- and the
    # sources are a multi-gigabyte download, so "just run it again" is not the
    # small thing it sounds like.
    out = _real_target(out)
    building = out.with_name(out.name + ".building")
    if building.exists():
        building.unlink()
    conn = open_db(building, create=True)
    conn.execute("PRAGMA synchronous = OFF")

    try:
        print("building language database", file=sys.stderr)
        coding = load_typology(conn, raw)
        load_unimorph(conn, raw)
        load_wiktionary(conn, raw,
                        keys=None if args.all_words else _curriculum_keys())
        print("  indexing (this is the slow part)", file=sys.stderr)
        conn.executescript(INDEXES)
        conn.commit()
        assemble(conn, coding)
        conn.execute("VACUUM")
        conn.close()
    except BaseException:
        conn.close()
        building.unlink(missing_ok=True)
        raise

    size = building.stat().st_size / 1e6
    os.replace(building, out)          # atomic on the same filesystem
    print(f"wrote {out} ({size:,.0f} MB)", file=sys.stderr)
    return 0


def _curriculum_keys() -> set[str]:
    """Every English word the curriculum puts on a page.

    Used when ``--all-words`` is off. The full harvest is the honest default
    for a general resource; this is the fast path for a build that only has to
    serve the lessons -- and it has to serve the section headings too, which
    an earlier version left out, so two hundred and twenty-five of the words
    the lessons head their blocks with were never fetched.
    """
    from langcurriculum.grammar.compile import rendered_vocabulary
    return rendered_vocabulary()


if __name__ == "__main__":
    raise SystemExit(main())
