#!/usr/bin/env python3
"""Cut a language database down to what the published site needs.

    python scripts/build_site_db.py --out site-languages.db
    python scripts/build_site_db.py --languages fin,deu,tur --out small.db

The full database is 8.4 GB, which is 56.7 million word forms and 3.1 million
senses for 411 languages. It is gitignored, so the Pages runner does not have
it, and without it the registry falls back to the seven hand-written packs --
the published site had seven languages where it should have had sixty-four.

The site does not need the whole thing. It renders 180 lessons, and those
ask the database for a bounded set of keys -- 5,045 of them, recorded by
instrumenting the store and rendering the curriculum rather than by guessing.
So this keeps

  * the languages being exported, and their profiles and typology;
  * senses whose key is one the renderer actually asks for;
  * word forms whose lemma is one of the translations of those senses --
    the only lemmas morphology is ever asked to inflect.

For 57 languages that is 38,458 senses and 706,152 forms: 77 MB, 17 MB
compressed, small enough to commit and hand to a runner.

Nothing is approximated. Every row kept is byte-identical to the row in the
full database, so a language renders the same from either; ``--verify``
checks that on real episodes rather than assuming it.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langcurriculum.grammar.compile import rendered_vocabulary      # noqa: E402
from langcurriculum.grammar.linearize import PREDICATE_GLOSS        # noqa: E402
from langcurriculum.registry import all_lessons                    # noqa: E402

SOURCE = ROOT / "langcurriculum" / "grammar" / "data" / "languages.db"


#: Languages to render the curriculum in while recording what it looks up.
#: One is not enough -- see the docstring below. These six take genuinely
#: different paths through the grammar: prepositional, case-marking,
#: classifier, agglutinative, noun-class, and a derived language that exercises
#: the database path rather than a hand-written pack.
PROBE_LANGUAGES = ("english", "spanish", "chinese", "turkish", "swahili", "fin")


def keys_used(probe_languages=PROBE_LANGUAGES, seeds: int = 50) -> set[str]:
    """Every key the renderer asks the lexicon for, recorded by asking it.

    Guessing this set is how the first two extracts shipped wrong. The coined
    vocabulary is 417 words and misses the field names; the rendered
    vocabulary is 715 and misses the closed class, so Finnish lost its copula
    and every question began "What" -- a language that looks translated until
    you read it, which is worse than one that plainly is not.

    Rendering the whole curriculum and recording what it looks up gives 1048
    keys, 426 of them outside the rendered set: quantifiers, comparators,
    role names like "actor of", the bare "P" and "Q" of a logic lesson.

    **One language does not establish the set**, which this file used to claim
    on the grounds that the keys are English. The keys are English; the
    *questions asked* are not. A case-marking language puts a location in the
    noun and never looks up a preposition, so probing Finnish alone never asks
    for "at" -- and Spanish, which does need it, shipped with an English "at"
    sitting in the middle of a Spanish sentence. So the probe runs over
    languages chosen to take different paths through the grammar, and
    ``--verify`` is what catches it when they are still not enough.

    Seeds matter as much as languages. Probing two seeds and publishing fifty
    left six lesson/language pairs differing, because a later episode coins a
    word an earlier one did not. So this probes exactly the seeds that will be
    published -- pass the same ``--samples`` the site is built with.
    """
    import langcurriculum as lc
    from langcurriculum.grammar.store import LanguageDB

    asked: set[str] = set()
    # Instrumented at the database, not at `Grammar`. A grammar reaches past
    # itself: the copula is looked up as "be" straight from the store, and
    # `disc` is mapped to the `disk` a dictionary keys on before the query is
    # made. Both bypass `Grammar.lookup`, and an extract built from what
    # `Grammar` asked for left Finnish with no copula and calling a kiekko a
    # disc.
    names = ("lookup", "lookup_all", "bulk_lookup", "paradigm", "surface_forms")
    originals = {name: getattr(LanguageDB, name) for name in names}

    def wrap(original, bulk: bool = False):
        def probe(self, code, key, *a, **k):
            asked.update(key) if bulk else asked.add(key)
            return original(self, code, key, *a, **k)
        return probe

    for name, original in originals.items():
        setattr(LanguageDB, name, wrap(original, bulk=name == "bulk_lookup"))
    try:
        for code in probe_languages:
            for lesson_id in lc.lesson_ids():
                for seed in range(seeds):
                    try:
                        lc.get(lesson_id).example(seed, language=code)
                    except Exception:              # a lesson that cannot render
                        pass                       # asks for nothing more
    finally:
        for name, original in originals.items():
            setattr(LanguageDB, name, original)

    return (asked | rendered_vocabulary() | set(PREDICATE_GLOSS.values())
            | {w for g in PREDICATE_GLOSS.values() for w in g.split()})


def with_pack_fallbacks(codes: list[str]) -> list[str]:
    """Add the ISO codes the hand-written packs fall back to.

    A pack is not self-sufficient. When its own vocabulary has no word for a key
    it asks the database under its ISO code -- ``spanish`` looks up ``spa`` --
    so exporting ``spanish`` without ``spa`` exports a pack that will fall
    through to nothing. That is how a Spanish sentence shipped with an English
    "at" in the middle of it: the row existed in the full database under a code
    the extract had never been told to copy.

    Only the packs that declare an ``iso`` reach for the database at all; the
    rest carry their own words and are unaffected.
    """
    from langcurriculum.grammar.grammars import GRAMMARS

    out = list(codes)
    for code in codes:
        grammar = GRAMMARS.get(code)
        iso = getattr(grammar, "iso", "") if grammar is not None else ""
        if iso and iso not in out:
            out.append(iso)
    return out


def _chunks(seq, n=800):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def extract(source: Path, target: Path, codes: list[str], seeds: int = 50) -> None:
    if target.exists():
        target.unlink()
    src = sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True)
    out = sqlite3.connect(target)
    out.execute("PRAGMA journal_mode=OFF")
    out.execute("PRAGMA synchronous=OFF")

    schema = [r[0] for r in src.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND type='table'")]
    for statement in schema:
        out.execute(statement)

    vocab = sorted(keys_used(seeds=seeds))
    print(f"  {len(vocab):,} lexicon keys the renderer asks for")
    kept = {"language": 0, "profile": 0, "typology": 0, "sense": 0, "wordform": 0}
    started = time.time()

    for code in codes:
        for table in ("language", "profile", "typology"):
            rows = src.execute(f"SELECT * FROM {table} WHERE code=?", (code,)).fetchall()
            if rows:
                out.executemany(
                    f"INSERT INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)
                kept[table] += len(rows)

        forms: set[str] = set()
        senses = []
        for part in _chunks(vocab):
            q = ",".join("?" * len(part))
            for row in src.execute(
                    f"SELECT * FROM sense WHERE code=? AND key IN ({q})", (code, *part)):
                senses.append(row)
                forms.add(row[3])                       # sense.form
        if senses:
            out.executemany(
                f"INSERT INTO sense VALUES ({','.join('?' * len(senses[0]))})", senses)
            kept["sense"] += len(senses)

        # A lemma is only ever inflected if some sense offered it as a word of
        # this language. Everything else in `wordform` is unreachable here.
        forms.discard("")
        ordered = sorted(forms)
        for part in _chunks(ordered):
            q = ",".join("?" * len(part))
            rows = src.execute(
                f"SELECT * FROM wordform WHERE code=? AND lemma IN ({q})",
                (code, *part)).fetchall()
            if rows:
                out.executemany(
                    f"INSERT INTO wordform VALUES ({','.join('?' * len(rows[0]))})", rows)
                kept["wordform"] += len(rows)
        print(f"  {code:16} {kept['sense']:>8,} senses  "
              f"{kept['wordform']:>10,} forms  ({time.time() - started:.0f}s)", flush=True)

    for statement in [r[0] for r in src.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND type='index'")]:
        out.execute(statement)
    out.commit()
    out.execute("VACUUM")
    out.close()
    src.close()
    print(f"  kept: " + ", ".join(f"{k} {v:,}" for k, v in kept.items()))
    print(f"  {target} is {target.stat().st_size / 1e6:.0f} MB")


def verify(target: Path, codes: list[str], n: int = 3) -> int:
    """Render real episodes from the extract and from the full database.

    A subset that renders differently is worse than no subset at all: the
    published site would disagree with the package it claims to show.
    """
    import os
    import subprocess

    lessons = sorted(all_lessons())[:8]
    script = (
        "import json,sys;import langcurriculum as lc;"
        "out={};"
        f"lessons={lessons!r};codes={codes!r};"
        "\nfor c in codes:\n"
        "    for l in lessons:\n"
        "        try: out[c+'/'+l]=[lc.get(l).example(i,language=c).observation "
        f"for i in range({n})]\n"
        "        except Exception as e: out[c+'/'+l]='ERR '+type(e).__name__\n"
        "print(json.dumps(out))")

    def run(db: Path) -> dict:
        import json
        env = dict(os.environ, PYTHONPATH=str(ROOT), LANGCURRICULUM_DB=str(db))
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                              text=True, env=env, cwd=ROOT)
        if proc.returncode:
            print(proc.stderr[-1500:], file=sys.stderr)
            raise SystemExit("verify: render failed")
        return json.loads(proc.stdout)

    print("  rendering from the full database...", flush=True)
    full = run(SOURCE)
    print("  rendering from the extract...", flush=True)
    small = run(target)
    bad = [k for k in full if full[k] != small.get(k)]
    if bad:
        print(f"  DIFFERS on {len(bad)} of {len(full)}: {bad[:6]}")
        for k in bad[:2]:
            print(f"    full : {str(full[k])[:180]}")
            print(f"    small: {str(small.get(k))[:180]}")
        return 1
    print(f"  identical on {len(full)} lesson/language pairs")
    return 0


def main() -> int:
    import importlib.util

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "site-languages.db"))
    ap.add_argument("--languages", default="",
                    help="comma-separated; default is what the site exports")
    ap.add_argument("--budget-mb", type=float, default=900.0)
    ap.add_argument("--samples", type=int, default=50)
    ap.add_argument("--verify", action="store_true",
                    help="render episodes from both databases and compare")
    args = ap.parse_args()

    if not SOURCE.exists():
        print(f"no database at {SOURCE}", file=sys.stderr)
        return 2

    if args.languages:
        codes = [c.strip() for c in args.languages.split(",") if c.strip()]
    else:
        spec = importlib.util.spec_from_file_location(
            "_bs", Path(__file__).resolve().parent / "build_site.py")
        bs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bs)
        codes = bs.choose(args.budget_mb, args.samples)
    codes = [c for c in codes if c not in {"symbols", "english_synonym"}]
    codes = with_pack_fallbacks(codes)

    target = Path(args.out)
    print(f"extracting {len(codes)} languages into {target}")
    extract(SOURCE, target, codes, args.samples)
    return verify(target, codes[:6]) if args.verify else 0


if __name__ == "__main__":
    raise SystemExit(main())
