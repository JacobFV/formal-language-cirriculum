#!/usr/bin/env python3
"""Regenerate the committed sample set under ``data/samples/``.

100 episodes per lesson, in every registered language, from seeds 0-99. These files are a
*published sample*, not the resource: the resource is the generators, and
anything here can be rebuilt byte-for-byte by running this script. Nothing
downstream should treat ``data/samples`` as the training set — use
``langcurriculum.export`` with your own seed range, and keep it disjoint from
whatever you evaluate on.

    python scripts/build_samples.py            # rebuild everything
    python scripts/build_samples.py -n 20      # a smaller set, for a quick look

The committed records omit ``observation`` (it is the prompt minus the trailing
answer-set instruction) because carrying it doubles the bytes for nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langcurriculum import __version__                        # noqa: E402
from langcurriculum.dataset import export                     # noqa: E402
from langcurriculum.registry import all_lessons, sections     # noqa: E402
from langcurriculum.languages import DEFAULT_LANGUAGE, language_codes, languages  # noqa: E402
from langcurriculum.verify import verify_lesson               # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", type=int, default=100, help="episodes per lesson (default 100)")
    ap.add_argument("--seed", type=int, default=0, help="first seed (default 0)")
    ap.add_argument("--out", default=str(ROOT / "data" / "samples"))
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the floor measurement in the manifest")
    args = ap.parse_args()

    out = Path(args.out)
    for code in language_codes():
        n = export(out / code, n=args.n, seed0=args.seed, language=code,
                   include_observation=False, per_lesson=True)
        print(f"{code:<16} {n} records", file=sys.stderr)

    lessons = all_lessons()
    manifest = {
        "version": __version__,
        "episodes_per_lesson": args.n,
        "seeds": [args.seed, args.seed + args.n - 1],
        "default_language": DEFAULT_LANGUAGE,
        "languages": languages(),
        "lessons": len(lessons),
        "implemented": sum(1 for l in lessons.values() if l.status == "implemented"),
        "sections": sections(),
        "lesson_info": {},
    }
    for lid, lesson in lessons.items():
        info = lesson.info()
        if not args.no_verify and lesson.status == "implemented":
            v = verify_lesson(lesson, episodes=200)
            info["floors"] = {k: v.get(k) for k in
                              ("uniform", "constant", "limit", "answer_set", "ok")}
        manifest["lesson_info"][lid] = info
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"manifest      {len(manifest['lesson_info'])} lessons", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
