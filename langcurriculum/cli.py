"""``langcurriculum`` on the command line: list, show, export, verify, evaluate."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Callable, Sequence

from . import __version__
from .dataset import export
from .evaluate import evaluate, random_agent
from .registry import all_lessons, get, resolve, sections
from .languages import DEFAULT_LANGUAGE, languages
from .verify import verify_all

__all__ = ["main"]


def _cmd_ls(args: argparse.Namespace) -> int:
    if args.sections:
        for s in sections():
            print(f"{s['section']:<14} {s['title']}  ({len(s['lessons'])} lessons)")
        return 0
    rows = resolve(args.lessons) if args.lessons else list(all_lessons().values())
    for l in rows:
        num = f"{l.number:>3}" if l.number else "  -"
        flag = "" if l.status == "implemented" else f"  [{l.status}]"
        print(f"{num}  {l.section:<14} {l.id:<36} {l.teaches}{flag}")
    print(f"\n{len(rows)} lessons", file=sys.stderr)
    return 0


def _cmd_languages(args: argparse.Namespace) -> int:
    for lang in languages():
        default = "  (default)" if lang["code"] == DEFAULT_LANGUAGE else ""
        print(f"{lang['code']:<18} {lang['kind']:<9} {lang['name']}{default}")
        print(f"{'':<18} {lang['description']}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    lesson = get(args.lesson)
    info = lesson.info()
    if args.json:
        ex = None if lesson.status != "implemented" else lesson.example(
            args.seed, language=args.language).to_dict()
        print(json.dumps({"info": info, "example": ex}, indent=2))
        return 0
    print(f"{info['id']}  (#{info['number'] or '-'}, level {info['level']}, "
          f"section {info['section']}: {info['section_title']})")
    print(f"teaches: {info['teaches']}")
    if info["capabilities"]:
        print(f"capabilities: {', '.join(info['capabilities'])}")
    if info["axes"]:
        print("axes: " + ", ".join(f"{k}={v}" for k, v in sorted(info["axes"].items())))
    if info["description"]:
        print("\n" + info["description"])
    if lesson.status != "implemented":
        print(f"\nstatus: {lesson.status}\n{lesson.note}")
        return 0
    for i in range(args.n):
        ex = lesson.example(args.seed + i, language=args.language)
        print(f"\n--- seed {ex.seed} ({ex.language}) " + "-" * 40)
        print(ex.prompt)
        print(f"answer: {ex.answer}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    total = export(args.out, args.lessons, n=args.n, seed0=args.seed,
                   language=args.language, include_hidden=not args.no_hidden,
                   per_lesson=args.per_lesson)
    print(f"wrote {total} records to {args.out}", file=sys.stderr)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    rows = verify_all(args.lessons, episodes=args.episodes)
    failed = [r for r in rows if r.get("ok") is False]
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            if r.get("ok") is None:
                print(f"{r['lesson']:<36} spec-only")
                continue
            mark = "ok " if r["ok"] else "FAIL"
            print(f"{r['lesson']:<36} {mark}  uniform={r.get('uniform')} "
                  f"constant={r.get('constant')} limit={r.get('limit')}")
    print(f"\n{len(rows) - len(failed)}/{len(rows)} passed", file=sys.stderr)
    return 1 if failed else 0


def _load_agent(spec: str) -> Callable[[str], str]:
    """``module:function`` -> the callable, imported at call time."""
    if spec == "random":
        return random_agent()
    if ":" not in spec:
        raise SystemExit(f"agent must be 'module:function' or 'random', got {spec!r}")
    mod, _, fn = spec.partition(":")
    obj: Any = importlib.import_module(mod)
    for part in fn.split("."):
        obj = getattr(obj, part)
    if not callable(obj):
        raise SystemExit(f"{spec} is not callable")
    return obj


def _cmd_eval(args: argparse.Namespace) -> int:
    agent = _load_agent(args.agent)
    report = evaluate(agent, args.lessons, n=args.n, seed0=args.seed,
                      language=args.language, strict=args.strict)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.table())
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="langcurriculum",
                                description="A procedurally generated language curriculum "
                                            "for evaluating and training text agents.")
    p.add_argument("--version", action="version", version=f"langcurriculum {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("-l", "--lessons", default=None,
                        help="lesson ids (comma-separated), a section key, or all")
        sp.add_argument("-L", "--language", default=DEFAULT_LANGUAGE,
                        help=f"language to read the episode in (default {DEFAULT_LANGUAGE})")
        sp.add_argument("--seed", type=int, default=0, help="first seed")

    sp = sub.add_parser("ls", help="list lessons")
    sp.add_argument("-l", "--lessons", default=None)
    sp.add_argument("--sections", action="store_true", help="list sections instead")
    sp.set_defaults(fn=_cmd_ls)

    sp = sub.add_parser("languages", help="list the languages an episode can be read in")
    sp.set_defaults(fn=_cmd_languages)

    sp = sub.add_parser("show", help="show one lesson and sample episodes")
    sp.add_argument("lesson")
    sp.add_argument("-n", type=int, default=1, help="episodes to print")
    sp.add_argument("-L", "--language", default=DEFAULT_LANGUAGE)
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=_cmd_show)

    sp = sub.add_parser("export", help="write a JSONL dataset")
    sp.add_argument("out")
    sp.add_argument("-n", type=int, default=100, help="episodes per lesson")
    sp.add_argument("--per-lesson", action="store_true",
                    help="write one file per lesson into a directory")
    sp.add_argument("--no-hidden", action="store_true",
                    help="omit the hidden ground truth from metadata")
    _common(sp)
    sp.set_defaults(fn=_cmd_export)

    sp = sub.add_parser("verify", help="check floors, determinism and generation")
    sp.add_argument("-l", "--lessons", default=None)
    sp.add_argument("--episodes", type=int, default=200)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=_cmd_verify)

    sp = sub.add_parser("eval", help="evaluate a text agent")
    sp.add_argument("agent", help="'module:function', or 'random' for the floor")
    sp.add_argument("-n", type=int, default=20, help="episodes per lesson")
    sp.add_argument("--strict", action="store_true", help="require exact-match replies")
    sp.add_argument("--json", action="store_true")
    _common(sp)
    sp.set_defaults(fn=_cmd_eval)

    args = p.parse_args(argv)
    return int(args.fn(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
