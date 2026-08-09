#!/usr/bin/env python3
"""Download the UniMorph paradigms ``build_langdb.py`` reads.

``build_langdb.py`` has always told you to run ``scripts/fetch_unimorph.sh``
and that file has never existed, so the documented way to rebuild the
database stopped at the largest of its three sources: fifty-six million of
the fifty-seven million word forms come from here. Without them the build
succeeds and the morphology is Wiktionary-only, which is a quieter failure
than a crash and a worse one.

One repository per language under github.com/unimorph, and the layout varies:
most keep a single file named after the code, and the big ones split it --
Finnish is ``fin.1`` and ``fin.2``. Sibling files (``.args``,
``.derivations``, ``.segmentations``) are different data and are not read by
the loader, so they are not fetched.

The language list is the one the shipped database was built from, written
down here so a rebuild reproduces it rather than whatever the organisation
happens to hold today.

    python scripts/fetch_unimorph.py --raw <dir>

Writes ``<dir>/unimorph/<iso>.tsv``, skipping anything already downloaded, so
an interrupted run can simply be repeated.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/unimorph"

#: The 170 languages the shipped database carries UniMorph forms for.
LANGUAGES = """
ady afb afr ail aka ame amh ang ara arn arz asm ast aym aze azg bak bel ben
bod bra bre bul cat ceb ces chu ckt cly cni cor cpa cre crh csb ctp cym czn
dak dan deu dje dsb ell eng est eus evn fao fas fra frm fro frr fry fur gaa
gal gla gle glv gmh gml goh got grc gsw guj gup hai hbs heb hil hin hsb hsi
hun hye ind isl ita itl izh jpn kal kan kat kaz kbd kca ket khk kir kjh klr
kmr kod kon kor krl lat lav lin lit liv lld lug mag mao mkd mlg mlt mwf nap
nav nds nld nno nob non nya oci ood orm osx ote pei pol por pus que ron rus
sah san see sga shp sjo slp slv sme sna sot spa sqi swc swe syc tat tel tgk
tgl tuk tur tyv uig ukr urd uzb vec vot vro wmt xcl xno xty yid zpv zul
""".split()


def _get(url: str) -> bytes | None:
    """The body, or ``None`` where the file is simply not there."""
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def fetch(code: str, out: Path) -> int:
    """One language's paradigms, joining a split file. Bytes written, or 0."""
    if out.exists() and out.stat().st_size:
        return out.stat().st_size
    parts: list[bytes] = []
    whole = _get(f"{BASE}/{code}/master/{code}")
    if whole is not None:
        parts.append(whole)
    else:
        # a language too large for one file: fin.1, fin.2, ...
        for n in range(1, 10):
            piece = _get(f"{BASE}/{code}/master/{code}.{n}")
            if piece is None:
                break
            parts.append(piece)
    if not parts:
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\n".join(parts))
    return out.stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True, help="the directory build_langdb reads")
    ap.add_argument("--only", nargs="*", help="just these codes, for a smoke test")
    args = ap.parse_args()

    codes = args.only or LANGUAGES
    udir = Path(args.raw) / "unimorph"
    total = missing = 0
    for i, code in enumerate(codes, 1):
        size = fetch(code, udir / f"{code}.tsv")
        total += size
        if not size:
            missing += 1
            print(f"  [{i}/{len(codes)}] {code}: no repository", file=sys.stderr)
        else:
            print(f"  [{i}/{len(codes)}] {code}: {size / 1e6:,.1f} MB",
                  file=sys.stderr)
    print(f"{len(codes) - missing} languages, {total / 1e9:,.2f} GB into {udir}",
          file=sys.stderr)
    if missing:
        print(f"{missing} had no repository under {BASE}; the build skips them",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
