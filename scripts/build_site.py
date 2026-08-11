#!/usr/bin/env python3
"""Freeze the curriculum viewer into ``docs/`` for GitHub Pages.

    python scripts/build_site.py                       # the default language set
    python scripts/build_site.py --languages eng,pol,jpn --samples 40
    python scripts/build_site.py --languages all        # see the warning below

This is not a second site. The design, the stylesheet and the page furniture
all come from :mod:`serve_site`, which is the same thing served live; this
script renders it ahead of time because GitHub Pages cannot run Python.

The one thing a static host cannot have is every language. The package speaks
412, and 180 lessons x 50 samples x 412 languages is 3.7 million episodes and
some gigabytes -- so the export carries a set chosen for typological spread,
and the local server keeps the rest:

    python scripts/serve_site.py

Each exported lesson is one page holding every exported language, and the
language select hides all but one. That is smaller than a page per language
(the chrome is written once, not once per language) and switching costs no
request at all -- which is what makes reading one episode across languages
bearable.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "_langcurriculum_site", Path(__file__).resolve().parent / "serve_site.py")
site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site)                                     # noqa: E402

import langcurriculum as lc                                        # noqa: E402
from langcurriculum.languages import language_codes  # noqa: F401
from langcurriculum.registry import all_lessons                    # noqa: E402
from langcurriculum.surfaces import RENDERER_VERSIONS              # noqa: E402

E = site.E

#: Roughly what one language costs: 180 lessons x 50 samples x ~1.5 kB.
BYTES_PER_EPISODE = 1550


def choose(budget_mb: float, samples: int) -> list[str]:
    """As many languages as fit, best-supported first, one family at a time.

    Everything the package speaks will not fit. 412 languages at 50 samples is
    about 5.7 GB and a GitHub Pages site may be 1 GB, so the export takes a
    budget and fills it.

    Filling it by coverage alone gives Finnish, German, French, Spanish,
    Russian, Polish, Portuguese, Italian, Dutch, Swedish -- an argument that
    the engine handles Europe. So families take turns: the best-covered
    language of each family, then the second of each, until the budget is
    spent. The hand-written grammars go first because they are the ones with
    verified behaviour to compare the rest against.
    """
    from collections import defaultdict

    from langcurriculum.grammar.store import LanguageDB

    per_language = len(all_lessons()) * samples * BYTES_PER_EPISODE
    room = max(1, int((budget_mb * 1e6 - len(all_lessons()) * 14_000) // per_language))

    chosen = [c for c in site.language_codes()]
    try:
        rows = {r["code"]: r for r in LanguageDB().languages()}
    except Exception:                                        # no database in CI
        return chosen[:room]
    known = {c for c, _l, _h in site._catalogue()}
    by_family: dict[str, list[str]] = defaultdict(list)
    def coverage(code: str) -> int:
        return (rows[code]["n_senses"] or 0) if code in rows else 0

    for code in sorted(known - set(chosen), key=lambda c: -coverage(c)):
        family = (rows[code]["family"] if code in rows else "") or "?"
        by_family[family].append(code)
    families = sorted(by_family, key=lambda f: -len(by_family[f]))
    rank = 0
    # Stop when a whole pass adds nothing. Testing `any(by_family.values())`
    # instead spun forever the moment the budget allowed more languages than
    # exist -- the lists are indexed, never emptied, so they stay truthy.
    while len(chosen) < room:
        added = 0
        for family in families:
            if len(chosen) >= room:
                break
            if rank < len(by_family[family]):
                chosen.append(by_family[family][rank])
                added += 1
        if not added:
            break
        rank += 1
    return chosen[:room]


def _sample(lesson, seed: int, code: str, lesson_id: str) -> str:
    """One episode, tagged with its language so the select can hide it."""
    rtl = ' dir="rtl"' if code in site._rtl() else ""
    try:
        prompt, answer = site._episode(lesson, seed, code)
    except Exception as exc:                                 # pragma: no cover
        return (f'<div class="sample" data-lang="{E(code)}">'
                f'<div class="head">seed <b>{seed:03d}</b>'
                f'<span class="grow"></span><span>{E(code)}</span></div>'
                f'<pre class="err">{E(type(exc).__name__)}: {E(str(exc))}</pre></div>')
    return (f'<div class="sample" data-lang="{E(code)}">'
            f'<div class="head">seed <b>{seed:03d}</b>'
            f'<span class="grow"></span><span>{E(site._label(code))}</span>'
            f'<span>{E(code)}</span></div>'
            f'<pre{rtl}>{E(prompt)}</pre>'
            f'<div class="answer">answer <b>{E(answer)}</b></div></div>')


#: What one sample of each surface costs, measured rather than guessed:
#: raster 1.7 KiB, video 15 KiB, scene 13 KiB, spoken nothing (it is text), and
#: audio 894 KiB -- thirty times the other four put together. So the cheap ones
#: ship by default and audio is asked for.
DEFAULT_SURFACES = ("raster", "spoken", "video", "scene")


def _surface_block(lesson, seed: int, code: str, surfaces) -> str:
    """One episode, shown through every surface that can carry it.

    The point of putting these side by side is that they share an
    ``instance_id``: it is the same problem, and a system that answers one and
    not another has learned the surface rather than the problem. That is the
    measurement the whole resource is bent toward, so the site ought to show it.
    """
    from langcurriculum.presentation import Presentation

    if lesson.status != "implemented":
        return ""                       # nothing to render, and it says why itself
    rows = []
    for name in surfaces:
        pres = Presentation(language=code, surface=name)
        try:
            text, target, content = site._rendered(lesson, seed, code, pres)
        except Exception as exc:
            rows.append(f'<div class="sample"><div class="head">{E(name)}</div>'
                        f'<div class="answer">not available here &mdash; '
                        f'{E(str(exc)[:120])}</div></div>')
            continue
        shown = (site._asset_html(content) if content is not None and content.assets
                 else f'<pre>{E(text)}</pre>')
        warn = ""
        if content is not None and not content.fidelity.lossless:
            warn = (f'<div class="answer">! {E("; ".join(content.fidelity.notes))}'
                    f'</div>')
        size = (f' &middot; {content.bytes_total // 1024} KiB'
                if content is not None and content.bytes_total else "")
        rows.append(f'<div class="sample"><div class="head"><b>{E(name)}</b>'
                    f'<span class="grow"></span>'
                    f'<span>{E(RENDERER_VERSIONS.get(name, ""))}{size}</span>'
                    f'</div>{shown}{warn}'
                    f'<div class="answer">target <b>{E(target)}</b></div></div>')
    if not rows:
        return ""
    ex = lesson.example(seed, language=code)
    return (f'<h2><span class="s">surfaces</span><span>the same episode, '
            f'carried differently &mdash; instance {E(ex.instance_id)}</span></h2>'
            + "".join(rows))


def _select(codes: list[str], chosen: str) -> str:
    opts = "".join(
        f'<option value="{E(c)}"{" selected" if c == chosen else ""}>'
        f'{E(site._label(c))}</option>' for c in codes)
    return (f'<select id="langsel">{opts}'
            f'<option value="*">&mdash; all {len(codes)}, side by side &mdash;</option>'
            f'</select>')


SWITCH = """<script>
(function () {
  var sel = document.getElementById('langsel'),
      box = document.querySelector('.samples');
  if (!sel || !box) return;
  var KEY = 'langcurriculum.lang';
  try { var s = localStorage.getItem(KEY); if (s) { sel.value = s; } } catch (e) {}
  function apply() {
    box.setAttribute('data-show', sel.value);
    document.querySelectorAll('[data-lang-label]').forEach(function (n) {
      n.textContent = sel.value === '*' ? 'all languages'
                    : sel.options[sel.selectedIndex].text;
    });
    document.querySelectorAll('a[data-lang-link]').forEach(function (a) {
      a.href = a.getAttribute('data-lang-link') + (sel.value === '*' ? '' :
               '#') ;
    });
    try { localStorage.setItem(KEY, sel.value); } catch (e) {}
  }
  sel.addEventListener('change', apply);
  apply();
})();
</script>"""


def lang_rules(codes: list[str]) -> str:
    """Un-hide the selected language.

    The shared stylesheet hides every sample under `[data-show]` and only
    knows how to show them all again for `data-show="*"`. CSS cannot compare
    a sample's `data-lang` against the container's `data-show`, so the pairing
    has to be spelled out one code at a time -- which only the export knows,
    since it picks which languages fit the budget.
    """
    def q(code: str) -> str:
        return code.replace("\\", "\\\\").replace('"', '\\"')
    return "\n".join(
        f'.samples[data-show="{q(c)}"] .sample[data-lang="{q(c)}"]'
        " { display: block; }" for c in codes) + "\n"


def lesson_page(lesson_id: str, codes: list[str], n: int, depth: int,
                surfaces=DEFAULT_SURFACES, surface_samples: int = 1) -> bytes:
    up = "../" * depth
    lesson = lc.get(lesson_id)
    axes = getattr(lesson, "axes", {}) or {}
    head = (f'<div class="head"><h1><span class="sig">{site._sig(lesson_id)}</span>'
            f'{E(lesson_id.replace("_", " "))}</h1>'
            f'<p class="lede">{E(getattr(lesson, "teaches", "") or "")}</p>'
            + site._spec(("language", "", True),
                         ("samples", str(n), False),
                         ("tags", ", ".join(getattr(lesson, "tags", ())) or "—", False),
                         ("difficulty knob",
                          "yes" if lesson.supports_difficulty() else "no", False),
                         *[(k.replace("_", " "), str(v), False)
                           for k, v in sorted(axes.items())],
                         ("capabilities",
                          ", ".join(getattr(lesson, "capabilities", ())) or "—", False))
            + "</div>")
    head = head.replace('<span class="v acc"></span>',
                        '<span class="v acc" data-lang-label>english</span>')
    top = (f'<header class="top">'
           f'<label class="burger" for="navtoggle" title="lessons">&#9776;</label>'
           f'<span class="field wide"><label class="q" for="langsel">language</label>'
           f'{_select(codes, codes[0])}</span>'
           f'<span class="grow"></span>'
           f'<span class="here">'
           f'<a href="{up}graph/{E(site.DEFAULT_CURRICULUM)}.html">graph &rarr;</a> '
           f'&middot; {site._sig(lesson_id)} &middot; <b>{n}</b> samples '
           f'&middot; <b>{len(codes)}</b> languages</span></header>')
    # grouped by seed, so "all languages" reads as a comparison of one episode
    blocks = "".join(_sample(lesson, seed, code, lesson_id)
                     for seed in range(n) for code in codes)
    blocks += "".join(_surface_block(lesson, seed, codes[0], surfaces)
                      for seed in range(min(n, surface_samples)))
    sidebar = site._sidebar(lesson_id, codes[0],
                            lambda lid, _c: f"{up}lessons/{lid}.html",
                            n_languages=len(codes), home=f"{up}index.html")
    return site._page(f"{site._sig(lesson_id)} {lesson_id} — langcurriculum",
                      sidebar, top,
                      head + f'<div class="body"><div class="samples" data-show='
                             f'"{E(codes[0])}">{blocks}</div></div>',
                      style=f"{up}style.css", script=site.AUTOSUBMIT + SWITCH)


def index_page(codes: list[str], n: int) -> bytes:
    head = (f'<div class="head"><h1><span class="sig">CURRICULUM</span>'
            f'{len(all_lessons())} lessons, generated</h1>'
            f'<p class="lede">Every lesson is a program, not a corpus: the episodes below '
            f'are produced by a unification grammar, so the same episode can be said in any '
            f'language the engine has a grammar for. This page set carries '
            f'{len(codes)} of them, ordered by the '
            f'<b>{E(site.DEFAULT_CURRICULUM)}</b> curriculum &mdash; lessons are flat, '
            f'and other curricula order the same lessons differently. The other '
            f'{len(site._catalogue()) - len(codes)} are a local server away &mdash; '
            f'<code>python scripts/serve_site.py</code>.</p>'
            + site._spec(("lessons", str(len(all_lessons())), False),
                         ("languages here", str(len(codes)), True),
                         ("samples each", str(n), False),
                         ("languages in the engine", str(len(site._catalogue())), False))
            + "</div>")
    from langcurriculum.curricula import curriculum_ids
    links = " &middot; ".join(
        f'<a href="graph/{E(name)}.html">{E(name)}</a>' for name in curriculum_ids())
    body = [f'<h2><span class="s">graphs</span><span>every curriculum, drawn: '
            f'{links}</span></h2>']
    for heading, ids in site._groups(site.DEFAULT_CURRICULUM):
        body.append(f'<h2><span class="s">{E(site.DEFAULT_CURRICULUM)}</span>'
                    f'<span>{E(heading)}</span></h2><div class="grid">')
        for lid in ids:
            teaches = getattr(lc.get(lid), "teaches", "") or ""
            body.append(f'<a href="lessons/{lid}.html">'
                        f'<div class="r">{site._sig(lid)}</div>'
                        f'<div class="t">{E(lid.replace("_", " "))}</div>'
                        f'<div class="c">{E(teaches[:70])}</div></a>')
        body.append("</div>")
    top = (f'<header class="top">'
           f'<label class="burger" for="navtoggle" title="lessons">&#9776;</label>'
           f'<span class="here">'
           f'<a href="graph/{E(site.DEFAULT_CURRICULUM)}.html">graph &rarr;</a> &middot; '
           f'<b>{len(all_lessons())}</b> lessons &middot; '
           f'<b>{len(codes)}</b> languages here &middot; '
           f'<b>{len(site._catalogue())}</b> in the engine</span></header>')
    sidebar = site._sidebar("", codes[0], lambda lid, _c: f"lessons/{lid}.html",
                            n_languages=len(codes), home="index.html")
    return site._page("langcurriculum", sidebar, top, head + "".join(body),
                      style="style.css", script="")


def graph_page(cur: str, codes: list[str], depth: int) -> bytes:
    """A curriculum's DAG, as a standalone page.

    The static export gets one per curriculum rather than a picker, because a
    picker needs a server to answer it and the whole point of this file is that
    there is not one.
    """
    up = "../" * depth
    page = site.graph_page(cur, codes[0],
                           href=lambda lid: f"{up}lessons/{lid}.html").decode("utf-8")
    # relink the chrome the served version points at absolute routes
    page = page.replace('href="/graph', f'href="{up}graph')
    page = page.replace('action="/graph"', 'action="."')
    page = page.replace('href="/"', f'href="{up}index.html"')
    return page.replace('href="/style.css"', f'href="{up}style.css"').encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--samples", type=int, default=50)
    ap.add_argument("--languages", default="",
                    help="comma-separated; default is whatever fits --budget-mb, "
                         "and 'all' is every language the engine speaks")
    ap.add_argument("--budget-mb", type=float, default=900.0,
                    help="stop adding languages past this size (Pages allows 1 GB)")
    ap.add_argument("--surfaces", default=",".join(DEFAULT_SURFACES),
                    help="modalities to show one sample of on each lesson page; "
                         "'none' for text only. audio is ~894 KiB an episode "
                         "against ~30 KiB for the other four together")
    ap.add_argument("--surface-samples", type=int, default=1,
                    help="how many seeds to render through the other surfaces")
    args = ap.parse_args()

    if args.languages == "all":
        codes = [c for c, _l, _h in site._catalogue()]
        want = len(all_lessons()) * args.samples * len(codes) * BYTES_PER_EPISODE / 1e6
        print(f"warning: 'all' is {len(codes)} languages, about {want:.0f} MB. "
              f"GitHub Pages allows 1000 MB.")
    elif args.languages:
        codes = [c.strip() for c in args.languages.split(",") if c.strip()]
    else:
        codes = choose(args.budget_mb, args.samples)
        print(f"{len(codes)} languages fit in {args.budget_mb:.0f} MB "
              f"at {args.samples} samples")
    known = {c for c, _l, _h in site._catalogue()}
    unknown = [c for c in codes if c not in known]
    if unknown:
        print(f"unknown languages: {unknown}", file=sys.stderr)
        return 2

    surfaces = tuple(x.strip() for x in args.surfaces.split(",")
                     if x.strip() and x.strip() != "none")
    unknown_surfaces = [x for x in surfaces if x not in site.surface_names()]
    if unknown_surfaces:
        print(f"unknown surfaces: {unknown_surfaces}", file=sys.stderr)
        return 2

    out = Path(args.out)
    lessons = out / "lessons"
    if lessons.exists():
        shutil.rmtree(lessons)
    lessons.mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_text("")
    (out / "style.css").write_text(site.STYLE + lang_rules(codes),
                                   encoding="utf-8")
    (out / "index.html").write_bytes(index_page(codes, args.samples))
    graphs = out / "graph"
    graphs.mkdir(parents=True, exist_ok=True)
    from langcurriculum.curricula import curriculum_ids
    for name in curriculum_ids():
        (graphs / f"{name}.html").write_bytes(graph_page(name, codes, 1))
    print(f"{len(curriculum_ids())} graph pages")

    started = time.time()
    for i, lid in enumerate(sorted(all_lessons()), 1):
        (lessons / f"{lid}.html").write_bytes(
            lesson_page(lid, codes, args.samples, 1, surfaces, args.surface_samples))
        if i % 30 == 0:
            print(f"  {i}/{len(all_lessons())} lessons  "
                  f"({time.time() - started:.0f}s)", flush=True)

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"wrote {len(all_lessons()) + 1 + len(curriculum_ids())} pages, {len(codes)} languages, "
          f"{args.samples} samples each -> {out} ({total / 1e6:.0f} MB, "
          f"{time.time() - started:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
