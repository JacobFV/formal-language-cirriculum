"""The command line, and the site that has to be rebuildable from the scripts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import langcurriculum as lc
from langcurriculum.cli import main

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def test_ls_lists_every_lesson(capsys):
    assert main(["ls"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == lc.N_REGISTERED
    assert "symbol_grounding" in out


def test_ls_curricula(capsys):
    assert main(["curricula"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == len(lc.curriculum_ids())
    assert "canonical" in out and "progressive" in out


def test_show_prints_an_episode_and_its_answer(capsys):
    assert main(["show", "unification", "-n", "2"]) == 0
    out = capsys.readouterr().out
    assert out.count("target:") == 2
    assert "structural symbolic matching" in out
    assert "(english/inline_bare/text)" in out, "the default view is English text"


def test_show_takes_a_language(capsys):
    assert main(["show", "quantification", "-L", "symbols"]) == 0
    assert "(symbols/inline_bare/text)" in capsys.readouterr().out


def test_languages_lists_the_packs(capsys):
    assert main(["languages"]) == 0
    out = capsys.readouterr().out
    assert "english" in out and "(default)" in out and "symbols" in out


def test_show_json_is_parseable(capsys):
    assert main(["show", "quantification", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["info"]["id"] == "quantification"
    assert d["example"]["answer"] in d["example"]["choices"]


def test_export_writes_a_file(tmp_path, capsys):
    out = tmp_path / "x.jsonl"
    assert main(["export", str(out), "-l", "tag:symbols", "-n", "2"]) == 0
    assert sum(1 for _ in out.open()) == 22


def test_verify_exits_zero_when_the_selection_passes(capsys):
    assert main(["verify", "-l", "tag:symbols", "--episodes", "40"]) == 0
    assert "FAIL" not in capsys.readouterr().out


def test_eval_with_the_random_agent_runs(capsys):
    assert main(["eval", "random", "-l", "tag:symbols", "-n", "5"]) == 0
    assert "macro-average" in capsys.readouterr().out


def test_the_console_script_is_wired_up():
    r = subprocess.run([sys.executable, "-m", "langcurriculum.cli", "--version"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and lc.__version__ in r.stdout


# ------------------------------------------------------------------ site
@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """Build a small site with the real exporter.

    These tests used to read a prebuilt ``docs/``. When the site moved to a
    workflow that directory stopped being committed, so the guard stopped
    finding it and five tests skipped silently -- leaving the exporter
    untested at the moment it began producing what is published. Two
    languages and two samples take a few seconds and test the thing itself.

    English and Spanish are hand-written packs, so this needs no language
    database and runs anywhere.
    """
    out = tmp_path_factory.mktemp("site")
    result = subprocess.run(
        [sys.executable, "scripts/build_site.py", "--out", str(out),
         "--languages", "english,spanish", "--samples", "2"],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr[-2000:]
    return out


def test_there_is_a_page_for_every_lesson(site):
    pages = {p.stem for p in (site / "lessons").glob("*.html")}
    assert pages == set(lc.REGISTRY)


def test_the_site_fetches_nothing_from_anywhere_else(site):
    """Self-contained means self-contained: no CDN, no font, no remote script.

    Inline script is allowed now -- the language select switches between the
    languages on the page, and doing that without JavaScript would mean a
    page per language. It must stay inline: a `src` pointing anywhere is a
    request the reader did not ask for, and the page has to render offline.
    """
    external = re.compile(r'(?:src|href)\s*=\s*"(?!#)(?:https?:)?//', re.I)
    remote_script = re.compile(r'<script[^>]*\ssrc\s*=', re.I)
    pages = list((site / "lessons").glob("*.html"))[:40] + [site / "index.html"]
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert not external.search(text), page.name
        assert not remote_script.search(text), page.name


def test_a_lesson_page_carries_every_language_it_was_built_with(site):
    """One page, every exported language, the select hiding all but one.

    Counted by ``data-lang``, which is what the language select actually keys
    on. Counting every ``.sample`` instead swept in the surface block, so the
    test would have gone green or red according to how many modalities the page
    happened to show.
    """
    text = (site / "lessons" / "symbol_grounding.html").read_text(encoding="utf-8")
    assert text.count('<div class="sample" data-lang=') == 4, "2 languages x 2 samples"
    assert 'data-lang="english"' in text and 'data-lang="spanish"' in text
    assert 'id="langsel"' in text
    assert "denotation" in text


def test_a_lesson_page_shows_the_same_episode_through_the_other_surfaces(site):
    """The point of the block: one instance, several surfaces, side by side."""
    import re

    text = (site / "lessons" / "symbol_grounding.html").read_text(encoding="utf-8")
    assert "the same episode, carried differently" in text
    assert re.search(r"instance [0-9a-f]{16}", text)
    for surface in ("raster", "spoken", "video", "scene"):
        assert f"<b>{surface}</b>" in text, surface
    # the media is inline, so the page still fetches nothing from anywhere
    assert "data:image/png;base64," in text
    assert "data:image/apng;base64," in text


def test_the_spec_only_lesson_shows_no_surfaces_rather_than_an_error(site):
    text = (site / "lessons" / "open_world_research_agent.html").read_text(
        encoding="utf-8")
    assert "the same episode, carried differently" not in text


def test_the_page_opens_on_the_first_language(site):
    text = (site / "lessons" / "symbol_grounding.html").read_text(encoding="utf-8")
    assert 'data-show="english"' in text, "the page should open on English"
    assert "In the scene:" in text


def test_the_index_links_every_lesson_page(site):
    text = (site / "index.html").read_text(encoding="utf-8")
    for lesson_id in lc.REGISTRY:
        assert f'href="lessons/{lesson_id}.html"' in text


def test_the_sidebar_reaches_every_lesson(site):
    """The lesson list is the navigation; a lesson missing from it is unreachable."""
    text = (site / "lessons" / "negation.html").read_text(encoding="utf-8")
    for lesson_id in lc.REGISTRY:
        assert f'href="../lessons/{lesson_id}.html"' in text, lesson_id


# ---------------------------------------------------------------- the graph view
def test_there_is_a_graph_page_for_every_curriculum(site):
    import langcurriculum as lc

    for name in lc.curriculum_ids():
        assert (site / "graph" / f"{name}.html").exists(), name


def test_the_graph_draws_every_node_and_every_edge(site):
    import re

    import langcurriculum as lc

    c = lc.curriculum("progressive")
    html = (site / "graph" / "progressive.html").read_text(encoding="utf-8")
    assert html.count('class="dag-node"') == len(c.nodes)
    assert html.count('class="dag-edge"') == len(c.edges)
    # and nothing spills outside the canvas it declares
    w, h = map(int, re.search(r'viewBox="0 0 (\d+) (\d+)"', html).groups())
    for x, y, bw, bh in re.findall(
            r'<rect class="dag-node" x="(\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"',
            html):
        assert 0 <= int(x) and int(x) + int(bw) <= w
        assert 0 <= int(y) and int(y) + int(bh) <= h


def test_the_layout_never_points_an_edge_backwards(site):
    """A layered drawing is only readable if every arrow goes one way."""
    import importlib.util

    import langcurriculum as lc

    spec = importlib.util.spec_from_file_location(
        "_graph_site", ROOT / "scripts" / "serve_site.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    c = lc.curriculum("progressive")
    order = mod._ordered_layers(c)
    column = {k: i for i, col in enumerate(order) for k in col}
    assert sorted(column) == sorted(c.keys)
    for a, b in c.edges:
        assert column[a] < column[b], f"{a} -> {b} points backwards"


def test_an_edgeless_curriculum_still_draws(site):
    """It is one column, and that is the curriculum declining to claim anything."""
    html = (site / "graph" / "canonical.html").read_text(encoding="utf-8")
    assert html.count('class="dag-node"') == 180
    assert html.count('class="dag-edge"') == 0


def test_every_graph_node_links_to_a_page_that_exists(site):
    import re

    html = (site / "graph" / "progressive.html").read_text(encoding="utf-8")
    hrefs = set(re.findall(r'<a href="\.\./lessons/([a-z_]+)\.html"', html))
    assert len(hrefs) == 180
    for lid in hrefs:
        assert (site / "lessons" / f"{lid}.html").exists(), lid


def test_the_graph_fetches_nothing_from_anywhere_else(site):
    """Same rule as the rest of the site: the SVG namespace is not a fetch."""
    html = (site / "graph" / "progressive.html").read_text(encoding="utf-8")
    stripped = html.replace("http://www.w3.org/2000/svg", "")
    assert "http://" not in stripped and "https://" not in stripped


def test_the_graph_is_reachable_by_clicking_rather_than_by_typing_a_url(site):
    """A page nothing links to is a page nobody finds.

    The graph pages shipped and were live for a deploy before anything on the
    site pointed at them.
    """
    import langcurriculum as lc

    index = (site / "index.html").read_text(encoding="utf-8")
    for name in lc.curriculum_ids():
        assert f'href="graph/{name}.html"' in index, name
    lesson = (site / "lessons" / "analogy.html").read_text(encoding="utf-8")
    assert 'href="../graph/' in lesson


def test_the_burger_is_a_real_touch_target_on_a_narrow_screen(site):
    """It was 15px tall and flat against the top edge.

    The top bar wraps on a narrow screen, and a stretched flex item alone on a
    row is only as tall as its glyph, so the burger collapsed to its font size.
    """
    css = (site / "style.css").read_text(encoding="utf-8")
    burger = css.split("label.burger {", 1)[1].split("}", 1)[0]
    assert "min-height" in burger, "the burger has no height of its own"
    assert int(burger.split("min-height:")[1].split("px")[0].strip()) >= 44


def test_the_language_control_can_use_the_width_the_page_has(site):
    css = (site / "style.css").read_text(encoding="utf-8")
    assert "header.top .field.wide" in css
    assert "max-width: 300px" not in css, "the select was pinned to a fixed width"
    page = (site / "lessons" / "analogy.html").read_text(encoding="utf-8")
    assert 'class="field wide"' in page


def test_the_sidebar_scrolls_with_the_sites_own_scrollbar(site):
    """An OS scrollbar through a page of hairlines reads as a seam."""
    css = (site / "style.css").read_text(encoding="utf-8")
    assert "scrollbar-width: thin" in css                     # Firefox
    assert "aside.side::-webkit-scrollbar" in css             # WebKit
    assert ".dagwrap::-webkit-scrollbar" in css               # and the graph canvas
