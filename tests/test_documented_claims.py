"""Every number the engine's documentation asserts, checked against the source.

This file exists because the same mistake happened three times. A docstring said
Chinese needed eleven overrides when it needed seven; the store said 16.4 million
word forms after a second source had brought it to 56.7; the override table was
written once and never recounted. None of those were caught by a test, because
none of them were *in* a test — they were prose, and prose does not fail.

The claims here are the ones a reader would reasonably act on: how much data
there is, how many constructions the abstract syntax has, how much idiosyncrasy
each grammar needs. Where a number is load-bearing for an argument the package
makes about itself — the override counts especially, since "few overrides" is
the evidence offered that the parameterization works — an understated or stale
figure is worse than no figure.

Tolerances are wide on purpose. The point is to catch a claim that has drifted
by an order of magnitude or a category, not to force a doc edit every time a
lesson gains a predicate.
"""

from __future__ import annotations

import ast
import collections
import pathlib
import random
import re

import pytest

import langcurriculum as lc
from conftest import DB, needs_db
from langcurriculum._structure import walk
from langcurriculum.grammar.grammars import GRAMMARS
from langcurriculum.grammar.linearize import Grammar
from langcurriculum.grammar.syntax import CONSTRUCTIONS

GRAMMAR_DIR = pathlib.Path(__file__).resolve().parent.parent / "langcurriculum" / "grammar"
LESSON_DIR = GRAMMAR_DIR.parent / "lessons"


def _doc(relative: str) -> str:
    return (GRAMMAR_DIR / relative).read_text(encoding="utf-8")


# ======================================================================
# the abstract syntax
# ======================================================================
def test_the_construction_count_matches_the_table_that_lists_them():
    """``syntax`` names a number and then tabulates them; the two must agree."""
    listed = {"Sym", "Lex", "CN", "NP", "AP", "Block"}
    core = CONSTRUCTIONS - listed
    words = {"Eighteen": 18, "Nineteen": 19, "Twenty": 20}
    doc = _doc("syntax.py")
    stated = next((n for w, n in words.items() if f"\n{w}. Adding a language" in doc), None)
    assert stated is not None, "syntax.py no longer states a construction count"
    assert stated == len(core), \
        f"docstring says {stated} constructions, the inventory has {len(core)}"


def test_every_construction_the_syntax_defines_can_be_linearized():
    """A construction nothing can render is worse than one that does not exist."""
    for code, grammar in GRAMMARS.items():
        missing = [c for c in CONSTRUCTIONS if not hasattr(grammar, f"lin_{c}")]
        assert not missing, f"{code} cannot linearize {missing}"


# ======================================================================
# the override counts, which are an argument and not decoration
# ======================================================================
def _overrides(stem: str) -> list[str]:
    base = {n for n in dir(Grammar) if not n.startswith("__")}
    path = GRAMMAR_DIR / "grammars" / f"{stem}.py"
    best: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef):
            found = [n.name for n in node.body
                     if isinstance(n, ast.FunctionDef)
                     and n.name in base and n.name != "__init__"]
            if len(found) > len(best):
                best = found
    return best


@pytest.mark.parametrize("stem", ["english", "spanish", "chinese", "turkish", "swahili"])
def test_the_documented_override_count_is_the_real_one(stem):
    """"Few overrides" is the evidence offered that the engine is parameterized.

    A table claiming Chinese needs eleven when it needs seven does not just
    mislead — it argues against the design it is meant to support, and invites
    the next reader to add a twelfth rather than ask why.
    """
    doc = _doc("grammars/__init__.py")
    row = re.search(rf":mod:`\.{stem}`\s+(\d+)", doc)
    assert row, f"the override table no longer lists {stem}"
    assert int(row.group(1)) == len(_overrides(stem)), (
        f"{stem}: table says {row.group(1)}, source has {len(_overrides(stem))} "
        f"({', '.join(_overrides(stem))})")


# ======================================================================
# the curriculum's own shape
# ======================================================================
def test_the_predicate_head_inventory_is_about_what_frames_claims():
    """``frames`` justifies inferring most frames by citing the long tail."""
    heads: collections.Counter = collections.Counter()
    for path in LESSON_DIR.rglob("*.py"):
        for m in re.finditer(r'\b(?:Pred|Rel|Node)\(\s*"([a-zA-Z_]\w*)"',
                             path.read_text(encoding="utf-8")):
            heads[m.group(1)] += 1
    doc = _doc("frames.py")
    claimed_heads = int(re.search(r"\*\*(\d+) distinct predicate heads", doc).group(1))
    claimed_sites = int(re.search(r"across (\d+) sites", doc).group(1))
    assert abs(claimed_heads - len(heads)) <= 20, \
        f"frames.py says {claimed_heads} heads, found {len(heads)}"
    assert abs(claimed_sites - sum(heads.values())) <= 30, \
        f"frames.py says {claimed_sites} sites, found {sum(heads.values())}"


def test_the_generic_paths_still_carry_the_share_syntax_claims():
    """``syntax`` opens by saying the four generic constructions carried 58%.

    That number is the motivation for the whole rewrite, so it should be within
    reach of the truth even as the frame lexicon grows.
    """
    generic = total = 0
    for lesson in [l for l in lc.all_lessons().values() if l.status == "implemented"][::3]:
        obs, _, _, _ = type(lesson).generate(random.Random(0))
        for term in walk(obs):
            if term.type not in ("pred", "rel", "node"):
                continue
            total += 1
            from langcurriculum.grammar.frames import FRAMES
            head = str(term.value[0])
            arity = len([a for a in term.value[1:] if hasattr(a, "type")])
            if f"{head}/{arity}" not in FRAMES and head not in FRAMES:
                generic += 1
    assert total, "no predicates found at all"
    share = generic / total
    assert 0.3 <= share <= 0.8, (
        f"{share:.0%} of predicate sites are frame-inferred; syntax.py's "
        f"account of why the rewrite was needed assumes roughly half")


# ======================================================================
# the data, which is the claim most likely to drift
# ======================================================================
@needs_db
def test_the_stores_description_of_its_own_size_is_current():
    doc = _doc("store.py")
    claimed = float(re.search(r"\*\*([\d.]+) million inflected forms", doc).group(1))
    actual = DB.conn.execute("SELECT COUNT(*) FROM wordform").fetchone()[0] / 1e6
    assert abs(claimed - actual) < max(1.0, actual * 0.1), \
        f"store.py says {claimed}M forms, the database holds {actual:.1f}M"


@needs_db
def test_the_per_source_counts_are_current():
    doc = _doc("store.py")
    by_source = dict(DB.conn.execute(
        "SELECT source, COUNT(*) FROM wordform GROUP BY source"))
    for name, key in (("UniMorph", "unimorph"), ("Wiktionary", "wiktionary")):
        claimed = float(re.search(rf"([\d.]+)M from {name}", doc).group(1))
        actual = by_source.get(key, 0) / 1e6
        assert abs(claimed - actual) < max(1.0, actual * 0.1), \
            f"store.py says {claimed}M from {name}, found {actual:.1f}M"


def test_the_vocabulary_size_vocab_cites_is_current():
    doc = _doc("grammars/vocab.py")
    claimed = int(re.search(r"carry (\d+) typed open-class entries", doc).group(1))
    actual = len(GRAMMARS["english"].vocabulary)
    assert claimed == actual, f"vocab.py says {claimed} entries, English has {actual}"
