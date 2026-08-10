#!/usr/bin/env python3
"""Capture, then hold to, what a lesson generates when no difficulty is asked for.

Adding a difficulty knob must not move the unset case. If it does, every corpus
already exported silently disagrees with the code that made it, and nothing
downstream would notice -- which is exactly the failure mode this whole resource
is built to avoid.

    python scripts/check_difficulty.py --capture baseline.json    # before editing
    python scripts/check_difficulty.py --check baseline.json      # after

``--check`` reports four things per lesson: whether the unset case still matches,
whether a difficulty actually moves the episode, whether the answer stays inside
its own option set at every difficulty, and whether the floor survives being
scaled. A lesson that fails the first is a regression; one that fails the rest
has a knob that is broken rather than absent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import langcurriculum as lc                                       # noqa: E402
from langcurriculum.verify import verify_lesson                   # noqa: E402

SEEDS = 6


def snapshot(seeds: int = SEEDS) -> dict:
    """What every implemented lesson produces with no difficulty asked for."""
    out: dict[str, list] = {}
    for lid in sorted(lc.lesson_ids(implemented_only=True)):
        rows = []
        for s in range(seeds):
            try:
                ex = lc.get(lid).example(s)
                rows.append([ex.prompt, ex.answer, list(ex.choices)])
            except Exception as e:                                # pragma: no cover
                rows.append(["ERROR", f"{type(e).__name__}: {e}", []])
        out[lid] = rows
    return out


def check(baseline: dict, seeds: int = SEEDS, floors: bool = True,
          only: set[str] | None = None) -> dict:
    now = snapshot(seeds)
    report: dict[str, dict] = {}
    for lid in sorted(set(baseline) | set(now)):
        if only and lid not in only:
            continue
        row: dict[str, object] = {}
        row["unset_unchanged"] = baseline.get(lid) == now.get(lid)
        lesson = lc.get(lid)
        row["has_knob"] = lesson.supports_difficulty()

        moved = False
        in_set = True
        errors: list[str] = []
        if row["has_knob"]:
            for d in (0.0, 1.0):
                for s in range(seeds):
                    try:
                        ex = lesson.example(s, difficulty=d)
                    except Exception as e:
                        errors.append(f"d={d} seed={s}: {type(e).__name__}: {e}")
                        continue
                    if ex.answer not in ex.choices:
                        in_set = False
            try:
                hard = [lesson.example(s, difficulty=1.0).prompt for s in range(seeds)]
                easy = [lesson.example(s, difficulty=0.0).prompt for s in range(seeds)]
                moved = hard != easy
            except Exception as e:
                errors.append(f"compare: {type(e).__name__}: {e}")
        row["moves"] = moved
        row["answer_in_set"] = in_set
        row["errors"] = errors[:2]
        if floors and row["has_knob"] and not errors:
            v = verify_lesson(lid, episodes=100, difficulty=1.0)
            row["floor_ok_at_hard"] = bool(v.get("ok"))
        report[lid] = row
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", metavar="PATH")
    ap.add_argument("--check", metavar="PATH")
    ap.add_argument("--seeds", type=int, default=SEEDS)
    ap.add_argument("--no-floors", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated lesson ids")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.capture:
        Path(args.capture).write_text(json.dumps(snapshot(args.seeds)))
        print(f"captured {len(snapshot(args.seeds))} lessons -> {args.capture}")
        return 0
    if not args.check:
        ap.error("one of --capture or --check is required")

    baseline = json.loads(Path(args.check).read_text())
    only = {x.strip() for x in args.only.split(',') if x.strip()} or None
    report = check(baseline, args.seeds, floors=not args.no_floors, only=only)
    if args.json:
        print(json.dumps(report, indent=1))

    regressed = [k for k, v in report.items() if not v["unset_unchanged"]]
    knobs = [k for k, v in report.items() if v["has_knob"]]
    inert = [k for k in knobs if not report[k]["moves"]]
    escaped = [k for k in knobs if not report[k]["answer_in_set"]]
    broke = [k for k in knobs if report[k].get("errors")]
    floors = [k for k in knobs if report[k].get("floor_ok_at_hard") is False]

    print(f"lessons            {len(report)}")
    print(f"with a knob        {len(knobs)}")
    print(f"UNSET CHANGED      {len(regressed)}  {regressed[:6]}")
    print(f"knob does nothing  {len(inert)}  {inert[:6]}")
    print(f"answer escaped set {len(escaped)}  {escaped[:6]}")
    print(f"raises when scaled {len(broke)}  {broke[:6]}")
    print(f"floor fails hard   {len(floors)}  {floors[:6]}")
    return 1 if (regressed or inert or escaped or broke or floors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
