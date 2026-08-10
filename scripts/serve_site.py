#!/usr/bin/env python3
"""Browse the curriculum in any of the languages the package can speak.

    python scripts/serve_site.py            # http://127.0.0.1:8765
    python scripts/serve_site.py --port 9000 --samples 100

Why this exists rather than more pages under ``docs/``: the static site is
built from the committed sample set, which covers the five hand-written
languages. Everything else the package speaks -- 411 grammars derived from
WALS, Grambank, UniMorph and Wiktionary -- has no committed samples and
cannot have any. 180 lessons x 50 samples x 411 languages is 3.7 million
episodes, about 3.5 GB of JSON before it is turned into HTML.

Generating one is 0.5 ms. So this renders on demand: any lesson, any
language, any seed, at whatever depth is asked for. A page of 50 samples
costs about 25 ms, and the first request for a given language pays an
extra 10-340 ms to build its grammar.

Nothing is written to disk and nothing leaves the machine.
"""

from __future__ import annotations

import argparse
import html
import sys
import traceback
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import langcurriculum as lc                                        # noqa: E402
from langcurriculum.languages import LANGUAGES, language_codes     # noqa: E402
from langcurriculum.curricula import curriculum_ids               # noqa: E402
from langcurriculum.curricula import get as get_curriculum         # noqa: E402
from langcurriculum.presentation import ANSWER_FORMATS, Presentation  # noqa: E402
from langcurriculum.registry import all_lessons                    # noqa: E402
from langcurriculum.surfaces import (NATIVE_SURFACES, render_native,  # noqa: E402
                                    renders_natively, surface_names,
                                    transcode_example)

E = html.escape

STYLE = """\
/* Instrument panel, not a brochure: hairline rules, tabular figures, every
   quantity labelled and in the same place on every page. */
*, *::before, *::after { box-sizing: border-box; border-radius: 0 !important; }
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #0a0a0a; --muted: #55555c; --faint: #8e8e96;
  --rule: #0a0a0a; --hair: #d8d8dc; --grid: #eeeef1;
  --accent: #0d33ff; --accent-fg: #ffffff; --flag: #c2410c;
  --code-bg: #f7f7f8; --side: #fbfbfc; --ok: #046c4e;
  --mono: ui-monospace, "SF Mono", "Cascadia Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Inter, Roboto, Arial, sans-serif;
  --side-w: 278px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #08080a; --fg: #ededf0; --muted: #9a9aa4; --faint: #63636d;
    --rule: #ededf0; --hair: #26262c; --grid: #141418;
    --accent: #7590ff; --accent-fg: #08080a; --flag: #fb923c;
    --code-bg: #101014; --side: #0c0c0f; --ok: #34d399;
  }
}
html, body { height: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font-family: var(--sans); font-size: 14px; line-height: 1.55;
  font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased;
}
a { color: inherit; text-decoration: none; }
.mono, .k { font-family: var(--mono); }

/* ---- frame ------------------------------------------------------------ */
.app { display: grid; grid-template-columns: var(--side-w) 1fr; min-height: 100vh; }
aside.side {
  border-right: 1px solid var(--rule); background: var(--side);
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  display: flex; flex-direction: column; z-index: 20;
}
aside .brand {
  padding: 13px 16px 11px; border-bottom: 1px solid var(--rule);
  position: sticky; top: 0; background: var(--side); z-index: 1;
}
aside .brand b { font-family: var(--mono); font-size: 12.5px; font-weight: 700;
                 text-transform: uppercase; letter-spacing: .13em; display: block; }
aside .brand .readout {
  display: flex; gap: 12px; margin-top: 7px; font-family: var(--mono);
  font-size: 10px; letter-spacing: .05em; color: var(--faint);
}
aside .brand .readout b { display: inline; font-size: 10px; letter-spacing: .05em;
                          color: var(--fg); font-weight: 600; }
aside .sec {
  display: flex; align-items: baseline; gap: 7px;
  padding: 13px 16px 5px; font-family: var(--mono); font-size: 10px;
  text-transform: uppercase; letter-spacing: .14em; color: var(--faint);
  border-top: 1px solid var(--hair); background: var(--grid);
}
aside .sec .s { color: var(--accent); font-weight: 700; }
aside a.item { display: flex; gap: 10px; padding: 3px 16px; font-size: 12.5px;
               color: var(--muted); border-left: 2px solid transparent; }
aside a.item .n { font-family: var(--mono); font-size: 10.5px; color: var(--faint);
                  min-width: 30px; letter-spacing: .03em; }
aside a.item:hover { background: var(--fg); color: var(--bg); }
aside a.item:hover .n { color: var(--bg); }
aside a.item.on { border-left-color: var(--accent); color: var(--fg); font-weight: 650;
                  background: var(--grid); }
aside a.item.on .n { color: var(--accent); font-weight: 700; }
aside .pad { flex: 1 1 auto; min-height: 30px; }
.col { min-width: 0; display: flex; flex-direction: column; }

/* ---- hamburger -------------------------------------------------------- */
.navtoggle { position: absolute; opacity: 0; pointer-events: none; }
label.burger {
  display: none; align-items: center; padding: 0 15px; cursor: pointer;
  border-right: 1px solid var(--hair); font-family: var(--mono); font-size: 15px;
  line-height: 1; user-select: none;
}
label.burger:hover { background: var(--fg); color: var(--bg); }
label.scrim { display: none; }

/* ---- top bar ---------------------------------------------------------- */
header.top {
  position: sticky; top: 0; z-index: 10; background: var(--bg);
  border-bottom: 1px solid var(--rule); display: flex; align-items: stretch;
  flex-wrap: wrap;
}
header.top form.picker { display: flex; align-items: stretch; flex-wrap: wrap; }
header.top .field { display: flex; align-items: center; border-right: 1px solid var(--hair); }
header.top label.q {
  font-family: var(--mono); font-size: 9.5px; text-transform: uppercase;
  letter-spacing: .16em; color: var(--faint); padding: 0 9px 0 15px;
}
select, input[type=number] {
  font-family: var(--mono); font-size: 12.5px; color: var(--fg);
  background: transparent; border: 0; padding: 11px 14px 11px 0;
  max-width: 300px; cursor: pointer;
}
select:focus, input:focus { outline: 2px solid var(--accent); outline-offset: -2px; }
button {
  font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: .14em; cursor: pointer; color: var(--bg); background: var(--fg);
  border: 0; padding: 0 16px;
}
button:hover { background: var(--accent); color: var(--accent-fg); }
header .grow { flex: 1 1 auto; }
header .here {
  display: flex; align-items: center; gap: 14px; padding: 0 16px; margin-left: auto;
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--faint); border-left: 1px solid var(--hair);
}
header .here b { color: var(--fg); font-weight: 650; }

/* ---- main ------------------------------------------------------------- */
main { padding: 0 0 90px; }
.head { padding: 24px 28px 20px; border-bottom: 1px solid var(--hair); }
h1 { font-size: 23px; letter-spacing: -.02em; margin: 0; font-weight: 680; }
h1 .dim { color: var(--faint); font-weight: 400; }
h1 .sig { font-family: var(--mono); font-size: 12px; color: var(--accent);
          letter-spacing: .08em; display: block; margin-bottom: 5px; font-weight: 600; }
p.lede { color: var(--muted); margin: 7px 0 0; max-width: 84ch; }
h2 { display: flex; align-items: baseline; gap: 9px;
     font-family: var(--mono); font-size: 10px; text-transform: uppercase;
     letter-spacing: .16em; color: var(--faint); margin: 0; font-weight: 600;
     padding: 9px 28px; background: var(--grid);
     border-top: 1px solid var(--hair); border-bottom: 1px solid var(--hair); }
h2 .s { color: var(--accent); font-weight: 700; }

/* spec strip: every page states its parameters in the same shape */
.spec { display: flex; flex-wrap: wrap; border-top: 1px solid var(--hair); }
.spec .cell { display: flex; flex-direction: column; gap: 2px;
              padding: 9px 20px 9px 0; margin-right: 20px;
              border-right: 1px solid var(--hair); }
.spec .cell:last-child { border-right: 0; }
.spec .k { font-size: 9.5px; text-transform: uppercase; letter-spacing: .16em;
           color: var(--faint); }
.spec .v { font-family: var(--mono); font-size: 12.5px; font-weight: 600; }
.spec .v.acc { color: var(--accent); }

.body { padding: 0 28px; }
.sample { border: 1px solid var(--hair); margin: 0 0 -1px; background: var(--bg); }
.sample:first-of-type { margin-top: 20px; }
.sample > .head {
  display: flex; align-items: center; gap: 14px; padding: 5px 14px;
  border: 0; border-bottom: 1px solid var(--hair); background: var(--grid);
  font-family: var(--mono); font-size: 10px; color: var(--faint);
  text-transform: uppercase; letter-spacing: .12em;
}
.sample > .head .grow { flex: 1 1 auto; }
.sample > .head b { color: var(--fg); font-weight: 650; }
.sample > .head a:hover { color: var(--accent); }
.sample pre { margin: 0; padding: 15px 18px; font-family: var(--mono); font-size: 13px;
              line-height: 1.72; white-space: pre-wrap; word-wrap: break-word; }
.sample .answer { padding: 6px 18px; border-top: 1px solid var(--hair);
                  background: var(--code-bg); font-family: var(--mono);
                  font-size: 11.5px; color: var(--faint);
                  text-transform: uppercase; letter-spacing: .1em; }
.sample .answer b { color: var(--ok); font-weight: 700; letter-spacing: .02em;
                    text-transform: none; font-size: 12.5px; }
[dir=rtl] pre { text-align: right; }

table.cmp { width: 100%; border-collapse: collapse; margin: 20px 0 0;
            border-top: 1px solid var(--hair); border-bottom: 1px solid var(--hair); }
table.cmp td { vertical-align: top; padding: 13px 18px;
               border-top: 1px solid var(--hair); font-family: var(--mono);
               font-size: 13px; line-height: 1.72; white-space: pre-wrap;
               word-wrap: break-word; }
table.cmp tr:first-child td { border-top: 0; }
table.cmp td.lang { white-space: nowrap; width: 1%; padding-right: 26px;
                    border-right: 1px solid var(--hair); background: var(--grid); }
table.cmp td.lang b { display: block; font-size: 12.5px; font-weight: 700; }
table.cmp td.lang .c { font-size: 10px; color: var(--faint); letter-spacing: .12em;
                       text-transform: uppercase; }
table.cmp tr:hover td { background: var(--code-bg); }

.grid { display: grid; gap: 0; grid-template-columns: repeat(auto-fill, minmax(252px, 1fr));
        border-bottom: 1px solid var(--hair); }
.grid a { padding: 11px 16px; border-right: 1px solid var(--hair);
          border-bottom: 1px solid var(--hair); display: block; }
.grid a:hover { background: var(--fg); color: var(--bg); }
.grid .r { font-family: var(--mono); font-size: 10px; color: var(--accent);
           letter-spacing: .1em; font-weight: 650; }
.grid a:hover .r, .grid a:hover .c { color: var(--bg); }
.grid .t { font-weight: 620; margin: 2px 0 3px; }
.grid .c { font-size: 12px; color: var(--muted); line-height: 1.45; }
/* static export: one page carries every exported language, and the select
   shows one at a time -- switching is instant and needs no second request */
.samples[data-show] .sample { display: none; }
.samples[data-show="*"] .sample { display: block; }
.sample .xl { display: none; }
.samples[data-show="*"] .sample .xl { display: inline; }
.err { font-family: var(--mono); font-size: 12px; white-space: pre-wrap;
       background: var(--code-bg); border: 1px solid var(--flag); padding: 14px;
       color: var(--flag); }

@media (max-width: 940px) {
  .app { grid-template-columns: 1fr; }
  aside.side {
    position: fixed; top: 0; left: 0; width: min(86vw, var(--side-w)); height: 100vh;
    transform: translateX(-101%); transition: transform .16s ease-out;
    border-right: 1px solid var(--rule);
  }
  .navtoggle:checked ~ .app aside.side { transform: none; }
  label.burger { display: flex; }
  .navtoggle:checked ~ .app label.scrim {
    display: block; position: fixed; inset: 0; z-index: 15;
    background: rgba(0,0,0,.42);
  }
  .head, .body, h2 { padding-left: 18px; padding-right: 18px; }
}
"""

AUTOSUBMIT = ("<script>for(const s of document.querySelectorAll('form.picker select,"
              "form.picker input[type=number]'))s.addEventListener('change',()=>s.form.submit())"
              "</script>")


# ---------------------------------------------------------------- languages
@lru_cache(maxsize=1)
def _catalogue() -> list[tuple[str, str, bool]]:
    """``(code, label, is_hand_written)`` for everything the package speaks."""
    from langcurriculum.grammar.registry import REGISTRY
    from langcurriculum.grammar.store import LanguageDB

    out = [(c, LANGUAGES[c].name if c in LANGUAGES else c, True)
           for c in language_codes()]
    named = {}
    try:
        for row in LanguageDB().languages():
            named[row["code"]] = row["name"] or row["code"]
    except Exception:                                        # pragma: no cover
        pass
    hand = {c for c, _l, _h in out}
    derived = sorted((c for c in REGISTRY.available if c not in hand),
                     key=lambda c: named.get(c, c).lower())
    out += [(c, f"{named.get(c, c)} ({c})", False) for c in derived]
    return out


@lru_cache(maxsize=1)
def _rtl() -> frozenset[str]:
    from langcurriculum.grammar.store import LanguageDB
    try:
        return frozenset(r["code"] for r in LanguageDB().languages() if r["rtl"])
    except Exception:                                        # pragma: no cover
        return frozenset()


def _label(code: str) -> str:
    for c, label, _h in _catalogue():
        if c == code:
            return label
    return code


def _select(name: str, chosen: str, *, autofocus: bool = False) -> str:
    hand = [o for o in _catalogue() if o[2]]
    derived = [o for o in _catalogue() if not o[2]]
    def opts(rows):
        return "".join(
            f'<option value="{E(c)}"{" selected" if c == chosen else ""}>{E(label)}</option>'
            for c, label, _h in rows)
    return (f'<select name="{name}"{" autofocus" if autofocus else ""}>'
            f'<optgroup label="hand-written">{opts(hand)}</optgroup>'
            f'<optgroup label="derived from data ({len(derived)})">{opts(derived)}</optgroup>'
            f'</select>')


# ---------------------------------------------------------------- curricula
DEFAULT_CURRICULUM = "canonical"


@lru_cache(maxsize=8)
def _positions(cur: str) -> dict:
    """lesson id -> its 1-based place in this curriculum's canonical flattening.

    A lesson has no number of its own any more, so a designator is a fact about
    the curriculum you are reading it in. Switch curriculum and the numbering
    changes, which is the honest behaviour: there was never one true order.
    """
    return {n.lesson: i for i, n in enumerate(get_curriculum(cur).linearize(), 1)}


@lru_cache(maxsize=8)
def _groups(cur: str) -> tuple:
    """``(heading, [lesson ids])`` for a curriculum, derived rather than declared.

    A curriculum with edges groups by graph layer, which is what its structure
    actually says. One without groups by the first tag its lessons carry, which
    is what the lessons actually say. Neither is a section: nothing here claims
    the lessons partition into one tree.
    """
    c = get_curriculum(cur)
    order = c.linearize()
    if c.edges:
        depth = c.layers()
        out: dict = {}
        for n in order:
            out.setdefault(f"layer {depth[n.key]}", []).append(n.lesson)
        return tuple((k, v) for k, v in
                     sorted(out.items(), key=lambda kv: int(kv[0].split()[1])))
    out = {}
    for n in order:
        tags = lc.get(n.lesson).tags
        out.setdefault(tags[0] if tags else "untagged", []).append(n.lesson)
    return tuple(out.items())


# ---------------------------------------------------------------- rendering
def _sig(lesson_id: str, cur: str = DEFAULT_CURRICULUM) -> str:
    """``L047`` — a stable designator within the curriculum being read."""
    n = _positions(cur).get(lesson_id)
    return f"L{n:03d}" if isinstance(n, int) else "L—"


def _lesson_href(lesson_id: str, code: str) -> str:
    return f"/lesson/{quote(lesson_id)}?lang={quote(code)}"


def _sidebar(current: str, code: str, href=None, *, n_languages: int | None = None,
             home: str = "/", cur: str = DEFAULT_CURRICULUM) -> str:
    """The lesson index. ``href`` lets the static export supply file paths."""
    href = href or _lesson_href
    n_lang = len(_catalogue()) if n_languages is None else n_languages
    groups = _groups(cur)
    out = [f'<aside class="side"><div class="brand"><a href="{home}"><b>langcurriculum</b></a>'
           f'<div class="readout"><span>lessons '
           f'<b>{sum(len(v) for _k, v in groups)}</b></span>'
           f'<span>languages <b>{n_lang}</b></span></div></div>']
    for heading, ids in groups:
        out.append(f'<div class="sec"><span class="s">{E(cur)}</span>'
                   f'<span>{E(heading)}</span></div>')
        for lid in ids:
            on = " on" if lid == current else ""
            out.append(f'<a class="item{on}" href="{href(lid, code)}">'
                       f'<span class="n">{_sig(lid, cur)}</span>'
                       f'<span>{E(lid.replace("_", " "))}</span></a>')
    out.append('<div class="pad"></div></aside>')
    return "".join(out)


def _plain_select(name: str, chosen: str, options) -> str:
    return (f'<select name="{name}">' + "".join(
        f'<option value="{E(o)}"{" selected" if o == chosen else ""}>{E(o)}</option>'
        for o in options) + "</select>")


def _topbar(action: str, code: str, *, n: int | None = None, extra: str = "",
            readout: str = "", cur: str = DEFAULT_CURRICULUM,
            fmt: str = "", surface: str = "") -> str:
    fields = (f'<span class="field"><label class="q">language</label>'
              f'{_select("lang", code)}</span>'
              f'<span class="field"><label class="q">curriculum</label>'
              f'{_plain_select("cur", cur, curriculum_ids())}</span>')
    if fmt:
        fields += (f'<span class="field"><label class="q">answers</label>'
                   f'{_plain_select("fmt", fmt, sorted(ANSWER_FORMATS))}</span>')
    if surface:
        fields += (f'<span class="field"><label class="q">surface</label>'
                   f'{_plain_select("surface", surface, surface_names())}</span>')
    if n is not None:
        fields += (f'<span class="field"><label class="q">samples</label>'
                   f'<input type="number" name="n" min="1" max="500" value="{n}"'
                   f' style="width:72px"></span>')
    return (f'<header class="top"><label class="burger" for="navtoggle"'
            f' title="lessons">&#9776;</label>'
            f'<form class="picker" method="get" action="{action}">'
            f'{extra}{fields}<noscript><button type="submit">go</button></noscript>'
            f'</form><span class="grow"></span>'
            f'<span class="here">{readout}</span></header>')


def _page(title: str, sidebar: str, topbar: str, body: str, *,
          style: str = "/style.css", script: str = AUTOSUBMIT) -> bytes:
    return (f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><link rel="stylesheet" href="{style}">
</head><body>
<input type="checkbox" id="navtoggle" class="navtoggle">
<div class="app">{sidebar}<label class="scrim" for="navtoggle"></label>
<div class="col">{topbar}<main>{body}</main></div></div>
{script}</body></html>""").encode("utf-8")


def _spec(*cells: tuple[str, str, bool]) -> str:
    return ('<div class="spec">' + "".join(
        f'<span class="cell"><span class="k">{E(k)}</span>'
        f'<span class="v{" acc" if acc else ""}">{E(v)}</span></span>'
        for k, v, acc in cells) + "</div>")


def _episode(lesson, seed: int, code: str, pres=None) -> tuple[str, str]:
    ex = lesson.example(seed, presentation=(pres or Presentation()).with_(language=code))
    return ex.observation, str(ex.answer)


def _rendered(lesson, seed: int, code: str, pres) -> tuple[str, str, object]:
    """The episode as its surface shows it, plus the content record."""
    ex = lesson.example(seed, presentation=pres.with_(language=code))
    if pres.surface == "text":
        return ex.prompt, ex.target, None
    if pres.surface in NATIVE_SURFACES:
        if not renders_natively(lesson, seed):
            raise ValueError(f"{lesson.id} builds nothing {pres.surface} can draw")
        content = render_native(lesson, seed, language=code, surface=pres.surface)
        return content.text, content.target or ex.target, content
    opts = {} if pres.surface == "audio" else {"columns": 64, "scale": 2}
    content = transcode_example(ex, pres.surface, **opts)
    return content.text, content.target or ex.target, content


#: Alt text has to say what the picture *is* without saying what it shows -- an
#: honest description of the answer would hand it to a reader who cannot see the
#: image, which is exactly the episode this page is meant to pose.
_ALT = {"raster": "the episode, rendered as an image",
        "video": "the episode, revealed a line at a time",
        "scene": "the scene the episode describes, drawn"}


def _asset_html(content) -> str:
    """Media inline as data URIs, so a page still fetches nothing from anywhere."""
    import base64
    if content is None or not content.assets:
        return ""
    alt = _ALT.get(content.surface, "the episode")
    out = []
    if content.surface == "audio":
        a = content.assets[0]
        b64 = base64.b64encode(a.data).decode()
        out.append(f'<audio controls preload="none" style="width:100%"'
                   f' src="data:{a.mime};base64,{b64}"></audio>')
        out.append(f'<div class="answer">{content.meta.get("seconds", "?")} seconds, '
                   f'synthesized by rule &mdash; no model</div>')
        out.append(f'<pre>{E(content.text)}</pre>')
        return "".join(out)
    if content.surface == "video":
        primary = next((a for a in content.assets if a.mime == "image/apng"), None)
        a = primary or content.assets[0]
        b64 = base64.b64encode(a.data).decode()
        out.append(f'<img alt="{alt}" style="max-width:100%"'
                   f' src="data:{a.mime};base64,{b64}">')
        out.append(f'<div class="answer"><b>{content.meta.get("frames", 0)}</b> frames, '
                   f'animated PNG</div>')
        return "".join(out)
    for a in content.assets:
        b64 = base64.b64encode(a.data).decode()
        out.append(f'<img alt="{alt}" style="max-width:100%"'
                   f' src="data:{a.mime};base64,{b64}">')
    return "".join(out)


def _sample_block(lesson, seed: int, code: str, *, lesson_id: str, pres=None) -> str:
    dirattr = ' dir="rtl"' if code in _rtl() else ""
    pres = pres or Presentation()
    try:
        prompt, answer, content = _rendered(lesson, seed, code, pres)
    except Exception as exc:                                 # pragma: no cover
        return (f'<div class="sample"><div class="head">seed <b>{seed:03d}</b></div>'
                f'<pre class="err">{E(type(exc).__name__)}: {E(str(exc))}</pre></div>')
    if content is not None and content.assets:
        shown = _asset_html(content)
    else:
        shown = f'<pre{dirattr}>{E(prompt)}</pre>'
    warn = ""
    if content is not None and not content.fidelity.lossless:
        warn = (f'<div class="answer">! this surface loses something the answer '
                f'may depend on: {E("; ".join(content.fidelity.notes))}</div>')
    return (f'<div class="sample"><div class="head">seed <b>{seed:03d}</b>'
            f'<span class="grow"></span><span>{E(code)}</span>'
            f'<a href="/compare/{quote(lesson_id)}/{seed}?from={quote(code)}">'
            f'compare &rarr;</a></div>'
            f'{shown}{warn}'
            f'<div class="answer">target <b>{E(answer)}</b></div></div>')


def index_page(code: str, cur: str = DEFAULT_CURRICULUM) -> bytes:
    c = get_curriculum(cur)
    head = (f'<div class="head"><h1><span class="sig">CURRICULUM</span>'
            f'{len(all_lessons())} lessons <span class="dim">in {E(_label(code))}</span></h1>'
            f'<p class="lede">Generated, not written. Lessons are flat; the order below '
            f'belongs to <b>{E(c.id)}</b> &mdash; {E(c.title)} &mdash; and other curricula '
            f'order the same lessons differently. Any sample opens beside the same episode '
            f'in any of the {len(_catalogue())} languages this package speaks.</p>'
            + _spec(("lessons", str(len(all_lessons())), False),
                    ("curriculum", c.id, True),
                    ("nodes", str(len(c.nodes)), False),
                    ("edges", str(len(c.edges)), False),
                    ("languages", str(len(_catalogue())), False),
                    ("hand-written", str(len(language_codes())), False))
            + "</div>")
    body = []
    for heading, ids in _groups(cur):
        body.append(f'<h2><span class="s">{E(cur)}</span>'
                    f'<span>{E(heading)}</span></h2><div class="grid">')
        for lid in ids:
            teaches = (getattr(lc.get(lid), "teaches", "") or "")
            body.append(f'<a href="/lesson/{quote(lid)}?lang={quote(code)}'
                        f'&amp;cur={quote(cur)}">'
                        f'<div class="r">{_sig(lid, cur)}</div>'
                        f'<div class="t">{E(lid.replace("_", " "))}</div>'
                        f'<div class="c">{E(teaches[:70])}</div></a>')
        body.append("</div>")
    return _page("langcurriculum", _sidebar("", code, cur=cur),
                 _topbar("/", code, cur=cur,
                         readout=f"<b>{len(all_lessons())}</b> lessons"),
                 head + "".join(body))


def lesson_page(lesson_id: str, code: str, n: int, cur: str = DEFAULT_CURRICULUM,
                pres: "Presentation | None" = None) -> bytes:
    lesson = lc.get(lesson_id)
    pres = pres or Presentation()
    axes = getattr(lesson, "axes", {}) or {}
    head = (f'<div class="head"><h1><span class="sig">{_sig(lesson_id, cur)}</span>'
            f'{E(lesson_id.replace("_", " "))}</h1>'
            f'<p class="lede">{E(getattr(lesson, "teaches", "") or "")}</p>'
            + _spec(("language", _label(code), True),
                    ("samples", str(n), False),
                    ("surface", pres.surface, pres.surface != "text"),
                    ("answers", pres.answer_format, False),
                    ("difficulty knob",
                     "yes" if lesson.supports_difficulty() else "no", False),
                    ("tags", ", ".join(lesson.tags) or "—", False),
                    *[(k.replace("_", " "), str(v), False) for k, v in sorted(axes.items())],
                    ("capabilities",
                     ", ".join(getattr(lesson, "capabilities", ())) or "—", False))
            + "</div>")
    blocks = "".join(_sample_block(lesson, s, code, lesson_id=lesson_id, pres=pres)
                     for s in range(n))
    return _page(f"{_sig(lesson_id, cur)} {lesson_id} - langcurriculum",
                 _sidebar(lesson_id, code, cur=cur),
                 _topbar(f"/lesson/{quote(lesson_id)}", code, n=n, cur=cur,
                         fmt=pres.answer_format, surface=pres.surface,
                         readout=f"{_sig(lesson_id, cur)} &middot; <b>{n}</b> samples"),
                 head + f'<div class="body">{blocks}</div>')


def compare_page(lesson_id: str, seed: int, codes: list[str]) -> bytes:
    lesson = lc.get(lesson_id)
    rows = []
    for code in codes:
        dirattr = ' dir="rtl"' if code in _rtl() else ""
        try:
            prompt, answer = _episode(lesson, seed, code)
            cell = f"{E(prompt)}\n\nanswer: {E(answer)}"
        except Exception as exc:                             # pragma: no cover
            cell = f"{E(type(exc).__name__)}: {E(str(exc))}"
        rows.append(f'<tr><td class="lang"><b>{E(_label(code))}</b>'
                    f'<span class="c">{E(code)}</span></td>'
                    f'<td{dirattr}>{cell}</td></tr>')
    keep = "".join(f'<input type="hidden" name="langs" value="{E(c)}">' for c in codes)
    top = (f'<header class="top"><label class="burger" for="navtoggle">&#9776;</label>'
           f'<form class="picker" method="get" '
           f'action="/compare/{quote(lesson_id)}/{seed}">{keep}'
           f'<span class="field"><label class="q">add language</label>'
           f'{_select("langs", "")}</span><button type="submit">add</button>'
           f'</form><span class="grow"></span>'
           f'<span class="here">seed <b>{seed:03d}</b> &middot; '
           f'<b>{len(codes)}</b> languages</span></header>')
    head = (f'<div class="head"><h1><span class="sig">{_sig(lesson_id)} &middot; '
            f'SEED {seed:03d}</span>{E(lesson_id.replace("_", " "))}</h1>'
            f'<p class="lede">One episode. One seed. Held constant while the language '
            f'varies &mdash; the only thing that differs below is who is speaking.</p>'
            + _spec(("seed", f"{seed:03d}", False),
                    ("languages", str(len(codes)), True),
                    ("lesson", lesson_id, False))
            + "</div>")
    return _page(f"{_sig(lesson_id)} seed {seed} - langcurriculum",
                 _sidebar(lesson_id, codes[0]), top,
                 head + f'<div class="body"><table class="cmp"><tbody>'
                 + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- transport
# ---------------------------------------------------------------- the graph view
#
# A curriculum is a DAG and a list cannot show that. Drawn as columns of layers
# with the edges between them, two things become visible that no ordering can
# say: how wide the graph is at each depth -- which is how much of the material
# is genuinely independent -- and which lessons are the joins everything funnels
# through.
#
# The SVG is written out rather than drawn by a library, for the same reason the
# rasterizer is: no external fetch, nothing to install, and the same bytes every
# time.

GRAPH_COL = 300
GRAPH_ROW = 21
GRAPH_PAD = 40
GRAPH_BOX = 188


def _ordered_layers(c) -> list:
    """Nodes grouped by depth, ordered to keep the edges from crossing.

    A barycentre sweep: put each node next to the average position of what it
    connects to, alternating up and down the layers. It is the classic layered
    layout heuristic and a handful of passes is enough -- the difference between
    a readable picture and a ball of wool.
    """
    depth = c.layers()
    layers: dict = {}
    for n in c.linearize():
        layers.setdefault(depth[n.key], []).append(n.key)
    order = [layers[d] for d in sorted(layers)]

    def sweep(forward: bool) -> None:
        span = range(1, len(order)) if forward else range(len(order) - 2, -1, -1)
        for i in span:
            other = order[i - 1] if forward else order[i + 1]
            place = {k: j for j, k in enumerate(other)}
            neighbours = c.prerequisites if forward else c.dependents

            def bary(key: str) -> float:
                ps = [place[p] for p in neighbours(key) if p in place]
                return sum(ps) / len(ps) if ps else len(place) / 2.0

            order[i] = sorted(order[i], key=lambda k: (bary(k), k))

    for _ in range(4):
        sweep(True)
        sweep(False)
    return order


def _graph_svg(cur: str, href=None) -> str:
    c = get_curriculum(cur)
    href = href or (lambda lid: f"/lesson/{quote(lid)}?cur={quote(cur)}")
    order = _ordered_layers(c)
    pos = {k: (i, j) for i, col in enumerate(order) for j, k in enumerate(col)}
    width = GRAPH_PAD * 2 + max(1, len(order)) * GRAPH_COL
    height = GRAPH_PAD * 2 + max((len(col) for col in order), default=1) * GRAPH_ROW + 30

    def xy(key: str) -> tuple[int, int]:
        i, j = pos[key]
        return GRAPH_PAD + i * GRAPH_COL, GRAPH_PAD + 30 + j * GRAPH_ROW

    parts = [f'<svg class="dag" viewBox="0 0 {width} {height}" width="{width}" '
             f'height="{height}" xmlns="http://www.w3.org/2000/svg" '
             f'font-family="ui-monospace, monospace">']
    for i, col in enumerate(order):
        x = GRAPH_PAD + i * GRAPH_COL
        parts.append(f'<text x="{x}" y="{GRAPH_PAD}" class="dag-layer">'
                     f'layer {i} &middot; {len(col)}</text>')
    for a, b in c.edges:
        if a not in pos or b not in pos:
            continue
        x1, y1 = xy(a)
        x2, y2 = xy(b)
        x1 += GRAPH_BOX
        mid = (x1 + x2) / 2
        parts.append(f'<path class="dag-edge" d="M{x1} {y1} C{mid} {y1} {mid} {y2} '
                     f'{x2} {y2}"/>')
    for key, (i, _j) in pos.items():
        node = c.node(key)
        x, y = xy(key)
        n_in, n_out = len(c.prerequisites(key)), len(c.dependents(key))
        label = node.lesson.replace("_", " ")
        label = label if len(label) <= 26 else label[:25] + "\u2026"
        parts.append(
            f'<a href="{E(href(node.lesson))}">'
            f'<title>{E(node.lesson)} &#10;{n_in} in, {n_out} out</title>'
            f'<rect class="dag-node" x="{x}" y="{y - 8}" width="{GRAPH_BOX}" '
            f'height="16" rx="3"/>'
            f'<text class="dag-text" x="{x + 7}" y="{y + 4}">{E(label)}</text>'
            f'</a>')
    parts.append("</svg>")
    return "".join(parts)


GRAPH_STYLE = """
.dagwrap { overflow: auto; border: 1px solid var(--rule); border-radius: 8px;
  background: var(--panel); padding: 4px; }
svg.dag { display: block; }
.dag-edge { fill: none; stroke: var(--faint); stroke-width: 1; opacity: .4; }
.dag-node { fill: var(--panel); stroke: var(--rule); }
.dag-text { font-size: 11px; fill: var(--fg); }
.dag-layer { font-size: 11px; fill: var(--accent); font-weight: 700; }
svg.dag a:hover .dag-node { fill: var(--accent); stroke: var(--accent); }
svg.dag a:hover .dag-text { fill: var(--accent-fg); }
"""

STYLE += GRAPH_STYLE


def graph_page(cur: str = "progressive", code: str = "english", href=None) -> bytes:
    """One curriculum, drawn. ``href`` lets the static export supply file paths."""
    c = get_curriculum(cur)
    depth = c.layers()
    widest = max((sum(1 for v in depth.values() if v == d)
                  for d in set(depth.values())), default=0)
    head = (f'<div class="head"><h1><span class="sig">GRAPH</span>'
            f'{E(c.id)}</h1>'
            f'<p class="lede">{E(c.title)}. Lessons are flat; this is one '
            f'curriculum\u2019s opinion about how they depend on each other, drawn '
            f'as layers. An edgeless curriculum is a single column &mdash; that is '
            f'not a bug, it is the curriculum declining to claim anything. '
            f'Every arrow points from a prerequisite to what it enables.</p>'
            + _spec(("curriculum", c.id, True),
                    ("nodes", str(len(c.nodes)), False),
                    ("edges", str(len(c.edges)), False),
                    ("layers", str(max(depth.values(), default=0) + 1), False),
                    ("widest layer", str(widest), False),
                    ("roots", str(len(c.roots())), False))
            + "</div>")
    body = f'<div class="body"><div class="dagwrap">{_graph_svg(cur, href)}</div></div>'
    top = (f'<header class="top">'
           f'<label class="burger" for="navtoggle" title="lessons">&#9776;</label>'
           f'<form class="picker" method="get" action="/graph">'
           f'<span class="field"><label class="q">curriculum</label>'
           f'{_plain_select("cur", cur, curriculum_ids())}</span>'
           f'<noscript><button type="submit">go</button></noscript></form>'
           f'<span class="grow"></span>'
           f'<span class="here"><b>{len(c.nodes)}</b> nodes &middot; '
           f'<b>{len(c.edges)}</b> edges</span></header>')
    side_href = (lambda lid, _c: href(lid)) if href else None
    return _page(f"graph \u00b7 {c.id} - langcurriculum",
                 _sidebar("", code, href=side_href, cur=cur), top, head + body)


DEFAULT_COMPARE = ["english", "spanish", "chinese", "turkish", "swahili"]


class Handler(BaseHTTPRequestHandler):
    server_version = "langcurriculum"

    def log_message(self, fmt, *args):                       # quieter
        pass

    def _send(self, body: bytes, kind: str = "text/html; charset=utf-8",
              status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:                                # noqa: N802
        url = urlparse(self.path)
        q = parse_qs(url.query)
        parts = [p for p in url.path.split("/") if p]
        try:
            if url.path == "/style.css":
                return self._send(STYLE.encode("utf-8"), "text/css; charset=utf-8")
            code = (q.get("lang") or ["english"])[0]
            cur = (q.get("cur") or [DEFAULT_CURRICULUM])[0]
            if cur not in curriculum_ids():
                cur = DEFAULT_CURRICULUM
            if not parts:
                return self._send(index_page(code, cur))
            if parts[0] == "graph" and len(parts) == 1:
                return self._send(graph_page(cur, code))
            if parts[0] == "lesson" and len(parts) == 2:
                n = max(1, min(500, int((q.get("n") or [self.server.samples])[0])))
                fmt = (q.get("fmt") or ["inline_bare"])[0]
                surface = (q.get("surface") or ["text"])[0]
                if fmt not in ANSWER_FORMATS:
                    fmt = "inline_bare"
                if surface not in surface_names():
                    surface = "text"
                pres = Presentation(language=code, answer_format=fmt, surface=surface)
                return self._send(lesson_page(parts[1], code, n, cur, pres))
            if parts[0] == "compare" and len(parts) == 3:
                codes = [c for c in q.get("langs", []) if c]
                if not codes:
                    first = (q.get("from") or ["english"])[0]
                    codes = [first] + [c for c in DEFAULT_COMPARE if c != first]
                seen, ordered = set(), []
                for c in codes:
                    if c not in seen:
                        seen.add(c)
                        ordered.append(c)
                return self._send(compare_page(parts[1], int(parts[2]), ordered))
            self._send(_page("not found", "<h1>404</h1>"), status=404)
        except Exception:                                    # pragma: no cover
            self._send(_page("error", f'<h1>500</h1><pre class="err">'
                                      f'{E(traceback.format_exc())}</pre>'), status=500)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--samples", type=int, default=50,
                    help="samples per lesson page (default 50)")
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.samples = args.samples
    n = len(_catalogue())
    print(f"langcurriculum: {len(all_lessons())} lessons in {n} languages, "
          f"{args.samples} samples a page")
    print(f"  http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
