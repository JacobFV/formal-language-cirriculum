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


def test_ls_sections(capsys):
    assert main(["ls", "--sections"]) == 0
    assert capsys.readouterr().out.count("\n") == 18


def test_show_prints_an_episode_and_its_answer(capsys):
    assert main(["show", "unification", "-n", "2"]) == 0
    out = capsys.readouterr().out
    assert out.count("answer:") == 2
    assert "structural symbolic matching" in out
    assert "(english)" in out, "the default view is English"


def test_show_takes_a_language(capsys):
    assert main(["show", "quantification", "-L", "symbols"]) == 0
    assert "(symbols)" in capsys.readouterr().out


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
    assert main(["export", str(out), "-l", "i", "-n", "2"]) == 0
    assert sum(1 for _ in out.open()) == 22


def test_verify_exits_zero_when_the_selection_passes(capsys):
    assert main(["verify", "-l", "i", "--episodes", "40"]) == 0
    assert "FAIL" not in capsys.readouterr().out


def test_eval_with_the_random_agent_runs(capsys):
    assert main(["eval", "random", "-l", "i", "-n", "5"]) == 0
    assert "macro-average" in capsys.readouterr().out


def test_the_console_script_is_wired_up():
    r = subprocess.run([sys.executable, "-m", "langcurriculum.cli", "--version"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and lc.__version__ in r.stdout


# ------------------------------------------------------------------ site
needs_site = pytest.mark.skipif(not (DOCS / "index.html").exists(),
                                reason="run scripts/build_site.py")


@needs_site
def test_there_is_a_page_for_every_lesson():
    pages = {p.stem for p in (DOCS / "lessons").glob("*.html")}
    assert pages == set(lc.REGISTRY)


@needs_site
def test_the_site_fetches_nothing_from_anywhere_else():
    """Self-contained means self-contained: no CDN, no font, no script."""
    external = re.compile(r'(?:src|href)\s*=\s*"(?!#)(?:https?:)?//', re.I)
    for page in list((DOCS / "lessons").glob("*.html"))[:40] + [DOCS / "index.html"]:
        text = page.read_text()
        assert not external.search(text), page.name
        assert "<script" not in text.lower(), page.name


@needs_site
def test_a_lesson_page_carries_its_hundred_samples():
    text = (DOCS / "lessons" / "symbol_grounding.html").read_text()
    assert text.count('<details class="sample">') == 100
    assert "denotation" in text


@needs_site
def test_the_site_shows_english_by_default():
    text = (DOCS / "lessons" / "symbol_grounding.html").read_text()
    assert "In the scene:" in text, "the samples on the page should be English"
    assert "The same episode, in each language" in text
    assert "<code>english</code>" in (DOCS / "index.html").read_text()


@needs_site
def test_the_index_links_every_lesson_page():
    text = (DOCS / "index.html").read_text()
    for lesson_id in lc.REGISTRY:
        assert f'href="lessons/{lesson_id}.html"' in text
