"""Datasets round-trip, and the committed samples are what they say they are."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import langcurriculum as lc
from langcurriculum.dataset import iter_records, read_jsonl, splits, write_jsonl
from langcurriculum.lesson import Example
from langcurriculum.languages import DEFAULT_LANGUAGE, language_codes

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def test_records_round_trip_through_jsonl(tmp_path):
    out = tmp_path / "d.jsonl"
    n = lc.export(out, "i", n=5)
    assert n == 11 * 5
    rows = read_jsonl(out)
    assert len(rows) == n
    for row in rows:
        ex = Example.from_dict(row)
        regenerated = lc.get(ex.lesson_id).example(ex.seed, language=ex.language)
        assert ex == regenerated, "a record must name the episode that produced it"


def test_export_per_lesson_writes_one_file_each(tmp_path):
    total = lc.export(tmp_path, "vii", n=4, per_lesson=True)
    files = sorted(p.name for p in tmp_path.glob("*.jsonl"))
    assert len(files) == 13 and total == 13 * 4
    assert files[0].endswith(".jsonl")
    assert all(len(read_jsonl(tmp_path / f)) == 4 for f in files)


def test_hidden_and_observation_can_be_dropped(tmp_path):
    out = tmp_path / "lean.jsonl"
    lc.export(out, "unification", n=3, include_hidden=False, include_observation=False)
    for row in read_jsonl(out):
        assert "observation" not in row
        assert "hidden" not in row["metadata"]
        assert row["prompt"] and row["answer"]


def test_the_spec_lesson_is_skipped_by_export(tmp_path):
    out = tmp_path / "cap.jsonl"
    lc.export(out, "xvii", n=2)
    ids = {r["lesson_id"] for r in read_jsonl(out)}
    assert "open_world_research_agent" not in ids
    assert len(ids) == 3


def test_train_and_eval_seed_ranges_cannot_overlap():
    s = splits(train=1000, eval=200)
    train0, train_n = s["train"]
    eval0, eval_n = s["eval"]
    assert train0 + train_n <= eval0
    assert set(range(train0, train0 + train_n)) & set(range(eval0, eval0 + eval_n)) == set()


def test_write_jsonl_creates_parents(tmp_path):
    p = tmp_path / "a" / "b" / "c.jsonl"
    assert write_jsonl(p, [{"x": 1}]) == 1
    assert read_jsonl(p) == [{"x": 1}]


def test_iter_records_is_lazy_and_ordered():
    it = iter_records("i", n=2)
    first = next(it)
    assert first["lesson_id"] == "symbol_grounding" and first["seed"] == 0


# ---------------------------------------------------- the committed samples
needs_samples = pytest.mark.skipif(
    not (SAMPLES / "manifest.json").exists(),
    reason="run scripts/build_samples.py to materialize data/samples")


@needs_samples
def test_the_committed_manifest_matches_the_registry():
    m = json.loads((SAMPLES / "manifest.json").read_text())
    assert m["lessons"] == lc.N_REGISTERED
    assert m["implemented"] == 179
    assert m["episodes_per_lesson"] == 100
    assert m["default_language"] == DEFAULT_LANGUAGE
    assert set(m["lesson_info"]) == set(lc.REGISTRY)


@needs_samples
@pytest.mark.parametrize("code", language_codes())
def test_every_implemented_lesson_has_100_committed_samples(code):
    d = SAMPLES / code
    ids = {p.stem for p in d.glob("*.jsonl")}
    assert ids == set(lc.lesson_ids(implemented_only=True))
    counts = {p.stem: sum(1 for _ in p.open()) for p in d.glob("*.jsonl")}
    assert set(counts.values()) == {100}


@needs_samples
def test_the_committed_samples_still_regenerate_exactly():
    """The files are a view of the generators; if they drift, they are wrong."""
    for lesson_id in ("symbol_grounding", "quantification", "theorem_proving",
                      "cultural_evolution", "symbolic_generalist", "palindrome"):
        rows = read_jsonl(SAMPLES / DEFAULT_LANGUAGE / f"{lesson_id}.jsonl")
        lesson = lc.get(lesson_id)
        for row in rows[:10]:
            ex = lesson.example(row["seed"])
            assert ex.prompt == row["prompt"]
            assert ex.answer == row["answer"]
            assert list(ex.choices) == row["choices"]
