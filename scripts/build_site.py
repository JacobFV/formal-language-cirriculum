#!/usr/bin/env python3
"""Build the static site under ``docs/`` from the committed sample set.

    python scripts/build_samples.py && python scripts/build_site.py

Everything the site needs is generated here: one index, one page per section,
one page per lesson carrying that lesson's 100 sampled episodes. There is no
JavaScript, no web font, and no request to any host — the only asset is a
same-origin stylesheet, so the pages render identically offline and on GitHub
Pages served from ``/docs``.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langcurriculum import N_NUMBERED, N_REGISTERED, __version__   # noqa: E402
from langcurriculum.dataset import read_jsonl                      # noqa: E402
from langcurriculum.registry import all_lessons, sections          # noqa: E402
from langcurriculum.languages import DEFAULT_LANGUAGE, language_codes, languages  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
E = html.escape

STYLE = """\
:root {
  --bg: #fbfbfa; --fg: #1c1b19; --muted: #6b6862; --rule: #ddd9d2;
  --card: #ffffff; --accent: #7a4b1e; --code-bg: #f4f2ee; --shadow: rgba(20,18,15,.05);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #17161a; --fg: #e8e6e1; --muted: #a09b93; --rule: #33312f;
    --card: #1f1e22; --accent: #d8a05e; --code-bg: #232227; --shadow: rgba(0,0,0,.3);
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
.wrap { max-width: 62rem; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 1.9rem; line-height: 1.25; margin: 0 0 .35rem; letter-spacing: -.015em; }
h2 { font-size: 1.25rem; margin: 2.5rem 0 .75rem; letter-spacing: -.01em; }
h3 { font-size: 1rem; margin: 1.75rem 0 .5rem; }
p { margin: 0 0 1rem; }
code, pre, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
pre {
  background: var(--code-bg); border: 1px solid var(--rule); border-radius: 6px;
  padding: .7rem .85rem; overflow-x: auto; font-size: .82rem; line-height: 1.5; margin: 0;
}
code { background: var(--code-bg); padding: .1em .35em; border-radius: 4px; font-size: .88em; }
pre code { background: none; padding: 0; }
.crumb { font-size: .85rem; color: var(--muted); margin-bottom: 1.5rem; }
.lede { font-size: 1.05rem; color: var(--muted); margin-bottom: 2rem; max-width: 44rem; }
.tags { display: flex; flex-wrap: wrap; gap: .4rem; margin: .75rem 0 1.25rem; }
.tag {
  font-size: .74rem; letter-spacing: .02em; padding: .18rem .5rem; border-radius: 999px;
  border: 1px solid var(--rule); color: var(--muted); background: var(--card);
}
.tag.spec { border-color: var(--accent); color: var(--accent); }
.stats { display: flex; flex-wrap: wrap; gap: 1.75rem; margin: 1.5rem 0 2rem;
         padding: 1rem 1.25rem; background: var(--card); border: 1px solid var(--rule);
         border-radius: 8px; }
.stat { min-width: 6rem; }
.stat .n { display: block; font-size: 1.5rem; font-weight: 600; letter-spacing: -.02em; }
.stat .k { font-size: .78rem; color: var(--muted); text-transform: lowercase; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
.scroll { overflow-x: auto; }
th, td { text-align: left; padding: .45rem .6rem; border-bottom: 1px solid var(--rule);
         vertical-align: top; }
th { font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted);
     font-weight: 600; }
td.num, th.num { text-align: right; color: var(--muted); width: 3.2rem; }
tbody tr:hover { background: var(--card); }
.sample { border: 1px solid var(--rule); border-radius: 8px; background: var(--card);
          margin: 0 0 .9rem; box-shadow: 0 1px 2px var(--shadow); }
.sample > summary { cursor: pointer; padding: .55rem .85rem; font-size: .85rem;
                    display: flex; gap: .9rem; align-items: baseline; }
.sample > summary::marker { color: var(--muted); }
.sample .seed { color: var(--muted); font-size: .78rem; min-width: 4.5rem; }
.sample .ans { font-family: ui-monospace, monospace; font-weight: 600; }
.sample .body { padding: 0 .85rem .85rem; }
.sample .body > p { margin: .5rem 0 .3rem; font-size: .76rem; color: var(--muted);
                    text-transform: uppercase; letter-spacing: .04em; }
.note { border-left: 3px solid var(--accent); padding: .1rem 0 .1rem 1rem;
        color: var(--muted); font-size: .92rem; }
footer { margin-top: 4rem; padding-top: 1.25rem; border-top: 1px solid var(--rule);
         color: var(--muted); font-size: .82rem; }
.secgrid { display: grid; gap: .6rem; grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr)); }
.seccard { border: 1px solid var(--rule); border-radius: 8px; padding: .8rem .95rem;
           background: var(--card); }
.seccard .r { font-size: .74rem; color: var(--muted); letter-spacing: .06em;
              text-transform: uppercase; }
.seccard .t { font-weight: 600; margin: .15rem 0 .2rem; }
.seccard .c { font-size: .8rem; color: var(--muted); }
ul.notes { margin: .4rem 0 0; padding-left: 1.1rem; font-size: .82rem; color: var(--muted); }
ul.notes li { margin: .1rem 0; }
"""


def page(title: str, body: str, *, depth: int = 0) -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<link rel="stylesheet" href="{up}style.css">
</head>
<body><div class="wrap">
{body}
<footer>
  <p>langcurriculum {E(__version__)} &middot; {N_NUMBERED} numbered lessons,
  {N_REGISTERED} registered &middot; every page on this site is generated by
  <code>scripts/build_site.py</code> from the committed samples.</p>
</footer>
</div></body>
</html>
"""


def tag(text: str, cls: str = "") -> str:
    return f'<span class="tag {cls}">{E(text)}</span>'


def sample_block(rec: dict, i: int) -> str:
    hid = (rec.get("metadata") or {}).get("hidden") or {}
    hidden = ""
    if hid:
        hidden = ("<p>hidden ground truth</p><pre>"
                  + E(json.dumps(hid, indent=1, sort_keys=True)) + "</pre>")
    return f"""<details class="sample">
<summary><span class="seed">seed {rec['seed']}</span>
<span>answer</span> <span class="ans">{E(str(rec['answer']))}</span></summary>
<div class="body">
<p>prompt</p><pre>{E(rec['prompt'])}</pre>
{hidden}
</div></details>"""


def lesson_page(lesson, info: dict, language_examples: dict[str, dict],
                recs: list[dict]) -> str:
    num = f"#{info['number']}" if info["number"] else "supplementary"
    tags = [tag(f"level {info['level']}"), tag(f"section {info['section']}")]
    tags += [tag(c) for c in info["capabilities"]]
    if info["status"] != "implemented":
        tags.append(tag(info["status"], "spec"))
    axes = "".join(f"<tr><td>{E(k)}</td><td class='num'>{v}</td></tr>"
                   for k, v in sorted(info["axes"].items()))
    floors = info.get("floors") or {}
    stats = ""
    if floors:
        stats = f"""<div class="stats">
<div class="stat"><span class="n">{floors.get('answer_set', '-')}</span>
  <span class="k">answers per episode</span></div>
<div class="stat"><span class="n">{floors.get('uniform', '-')}</span>
  <span class="k">uniform-guess floor</span></div>
<div class="stat"><span class="n">{floors.get('constant', '-')}</span>
  <span class="k">constant-guess floor</span></div>
<div class="stat"><span class="n">{len(recs)}</span>
  <span class="k">samples below</span></div>
</div>"""

    surf = ""
    for code in language_codes():
        ex = language_examples.get(code)
        if ex:
            surf += f"<h3>{E(code)}</h3><pre>{E(ex['prompt'])}</pre>"

    if info["status"] != "implemented":
        samples = (f'<p class="note">{E(info["note"])}</p>')
        surf = ""
        links = ""
    else:
        samples = "\n".join(sample_block(r, i) for i, r in enumerate(recs))
        links = ("<p>The same 100 episodes are committed as JSONL in the "
                 "repository, one file per language: "
                 + " &middot; ".join(f"<code>data/samples/{c}/{lesson.id}.jsonl</code>"
                                     for c in language_codes()) + "</p>")

    desc = E(info["description"]).replace("\n\n", "</p><p>")
    body = f"""<p class="crumb"><a href="../index.html">langcurriculum</a> &rsaquo;
  <a href="../index.html#{E(info['section'])}">{E(info['section_title'])}</a> &rsaquo;
  {E(lesson.id)}</p>
<h1>{E(num)} <code>{E(lesson.id)}</code></h1>
<p class="lede">{E(info['teaches'])}</p>
<div class="tags">{''.join(tags)}</div>
{stats}
<h2>What it generates</h2>
<p>{desc}</p>
<h2>Difficulty axes</h2>
<div class="scroll"><table><thead><tr><th>axis</th><th class="num">level</th></tr></thead>
<tbody>{axes or '<tr><td colspan="2">none declared</td></tr>'}</tbody></table></div>
{'<h2>The same episode, in each language</h2>' + surf if surf else ''}
<h2>Samples</h2>
{links}
{samples}
"""
    return page(f"{lesson.id} — langcurriculum", body, depth=1)


def index_page(lessons: dict, infos: dict, secs: list[dict]) -> str:
    cards = ""
    for s in secs:
        n_impl = sum(1 for lid in s["lessons"] if lessons[lid].status == "implemented")
        cards += (f'<a class="seccard" href="#{E(s["section"])}">'
                  f'<div class="r">{E(s["section"])}</div>'
                  f'<div class="t">{E(s["title"])}</div>'
                  f'<div class="c">{len(s["lessons"])} lessons</div></a>')

    blocks = ""
    for s in secs:
        rows = ""
        for lid in s["lessons"]:
            info = infos[lid]
            floors = info.get("floors") or {}
            num = info["number"] or "&mdash;"
            flag = "" if info["status"] == "implemented" else " <em>(spec)</em>"
            rows += (f'<tr><td class="num">{num}</td>'
                     f'<td><a href="lessons/{E(lid)}.html"><code>{E(lid)}</code></a>{flag}</td>'
                     f'<td>{E(info["teaches"])}</td>'
                     f'<td class="num">{info["level"]}</td>'
                     f'<td class="num">{floors.get("uniform", "&mdash;")}</td></tr>')
        blocks += (f'<h2 id="{E(s["section"])}">{E(s["section"])}. {E(s["title"])}</h2>'
                   f'<div class="scroll"><table><thead><tr><th class="num">#</th><th>lesson</th>'
                   f'<th>teaches</th><th class="num">level</th><th class="num">floor</th></tr></thead>'
                   f'<tbody>{rows}</tbody></table></div>')

    n_impl = sum(1 for l in lessons.values() if l.status == "implemented")
    n_langs = len(language_codes())
    langrows = ""
    for l in languages():
        vocab = l.get("vocabulary") or {}
        size = vocab.get("total") or 0
        notes = "".join(f"<li>{E(g)}</li>" for g in l.get("grammar") or [])
        langrows += (
            f'<tr><td><code>{E(l["code"])}</code>'
            + (" <em>(default)</em>" if l["code"] == DEFAULT_LANGUAGE else "")
            + f'</td><td>{E(l["kind"])}</td>'
            + f'<td class="num">{size or "&mdash;"}</td>'
            + f'<td>{E(l["description"])}'
            + (f'<ul class="notes">{notes}</ul>' if notes else "")
            + "</td></tr>")
    body = f"""<h1>langcurriculum</h1>
<p class="lede">A language curriculum for text agents: {N_NUMBERED} numbered lessons
that build from denotation and sequence memory up through recursion, quantification,
causality, proof, argument and self-modeling. Every lesson is a generator, not a
dataset &mdash; an episode is a pure function of a seed, the vocabulary is invented
per episode, the answer is computed from the construction rather than annotated,
and it is read in English by default.</p>

<div class="stats">
<div class="stat"><span class="n">{N_NUMBERED}</span><span class="k">numbered lessons</span></div>
<div class="stat"><span class="n">{N_REGISTERED}</span><span class="k">registered</span></div>
<div class="stat"><span class="n">{n_impl}</span><span class="k">implemented</span></div>
<div class="stat"><span class="n">{len(secs)}</span><span class="k">sections</span></div>
<div class="stat"><span class="n">{n_langs}</span><span class="k">languages</span></div>
</div>

<h2>Two things you can do with it</h2>
<p><strong>Evaluate a text agent.</strong> Hand it anything that maps a string to a
string and get back per-lesson accuracy with the floor beside it &mdash; because an
accuracy without a floor is not a result when the answer set varies per episode.</p>
<pre><code>pip install git+https://github.com/JacobFV/formal-language-cirriculum

import langcurriculum as lc
report = lc.evaluate(my_agent, n=20)
print(report.table())</code></pre>
<p><strong>Generate training data.</strong> Emit as many episodes as you like, from a
seed range disjoint from whatever you will evaluate on.</p>
<pre><code>lc.export("train.jsonl", n=1000, seed0=0)
lc.export("eval.jsonl",  n=200,  seed0=1_000_000)</code></pre>

<h2>Languages</h2>
<p>An episode is read in a <strong>language</strong>, and the default is English
prose. The language is a parameter of the resource rather than a formatting
option, so a lesson can be held fixed while the language varies &mdash; which is
how you separate a capability from having memorized the words it was trained in.</p>
<div class="scroll"><table><thead><tr><th>code</th><th>kind</th>
<th class="num">words</th><th>what it is, and the grammar it implements</th>
</tr></thead><tbody>{langrows}</tbody></table></div>

<h2>Sections</h2>
<div class="secgrid">{cards}</div>

{blocks}

<h2>The samples on this site</h2>
<p>Every lesson page carries 100 episodes generated from seeds 0&ndash;99 in
English, plus the same first episode in all
every registered language, and links the JSONL underneath. They are a <em>published sample</em>,
not the resource: the resource is the generator, and these files can be rebuilt
byte-for-byte with <code>python scripts/build_samples.py</code>. Do not train on
seeds 0&ndash;99 and then evaluate on them.</p>
"""
    return page("langcurriculum", body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--samples", default=str(SAMPLES))
    args = ap.parse_args()

    samples = Path(args.samples)
    manifest_path = samples / "manifest.json"
    if not manifest_path.exists():
        print(f"no manifest at {manifest_path}; run scripts/build_samples.py first",
              file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text())
    infos = manifest["lesson_info"]

    out = Path(args.out)
    (out / "lessons").mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_text("")
    (out / "style.css").write_text(STYLE)

    lessons = all_lessons()
    secs = sections()

    for lid, lesson in lessons.items():
        info = infos.get(lid) or lesson.info()
        recs: list[dict] = []
        language_examples: dict[str, dict] = {}
        if lesson.status == "implemented":
            recs = read_jsonl(samples / DEFAULT_LANGUAGE / f"{lid}.jsonl")
            for code in language_codes():
                rows = read_jsonl(samples / code / f"{lid}.jsonl")
                if rows:
                    language_examples[code] = rows[0]
        (out / "lessons" / f"{lid}.html").write_text(
            lesson_page(lesson, info, language_examples, recs))

    (out / "index.html").write_text(index_page(lessons, infos, secs))
    print(f"wrote {len(lessons) + 1} pages to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
