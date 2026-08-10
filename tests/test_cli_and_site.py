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
    """One page, every exported language, the select hiding all but one."""
    text = (site / "lessons" / "symbol_grounding.html").read_text(encoding="utf-8")
    assert text.count('<div class="sample"') == 4, "2 languages x 2 samples"
    assert 'data-lang="english"' in text and 'data-lang="spanish"' in text
    assert 'id="langsel"' in text
    assert "denotation" in text


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
