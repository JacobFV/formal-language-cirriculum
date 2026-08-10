"""Datasets round-trip, and the committed samples are what they say they are."""

from __future__ import annotations

import json
import os
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
    n = lc.export(out, "tag:symbols", n=5)
    assert n == 11 * 5
    rows = read_jsonl(out)
    assert len(rows) == n
    for row in rows:
        ex = Example.from_dict(row)
        regenerated = lc.get(ex.lesson_id).example(ex.seed, language=ex.language)
        assert ex == regenerated, "a record must name the episode that produced it"


def test_export_per_lesson_writes_one_file_each(tmp_path):
    total = lc.export(tmp_path, "tag:mathematics", n=4, per_lesson=True)
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
    lc.export(out, "tag:capstone", n=2)
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
    it = iter_records("tag:symbols", n=2)
    first = next(it)
    assert first["lesson_id"] == lc.resolve("tag:symbols")[0].id
    assert first["seed"] == 0


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
    """The files are a view of the generators; if they drift, they are wrong.

    Every lesson, not a handful. This checked six of a hundred and seventy-nine
    and stayed green through twenty commits that changed what the generators
    produce, so the committed dataset -- the artefact people actually download
    -- was stale in seven hundred and fifty-eight files before anyone noticed.
    Two seeds each keeps it quick enough to run every time.
    """
    stale = []
    for lesson_id in sorted(lc.lesson_ids(implemented_only=True)):
        path = SAMPLES / DEFAULT_LANGUAGE / f"{lesson_id}.jsonl"
        if not path.exists():
            continue
        lesson = lc.get(lesson_id)
        for row in read_jsonl(path)[:2]:
            ex = lesson.example(row["seed"])
            if (ex.prompt, ex.answer, list(ex.choices)) != (
                    row["prompt"], row["answer"], row["choices"]):
                stale.append(lesson_id)
                break
    assert not stale, (f"{len(stale)} lessons have drifted from their samples; "
                       f"rebuild with scripts/build_samples.py: {stale[:8]}")


@needs_samples
@pytest.mark.parametrize("code", ["spanish", "chinese", "turkish"])
def test_the_other_languages_regenerate_too(code):
    """The drift was in every language, and only English was ever checked."""
    stale = []
    for lesson_id in sorted(lc.lesson_ids(implemented_only=True))[::6]:
        path = SAMPLES / code / f"{lesson_id}.jsonl"
        if not path.exists():
            continue
        lesson = lc.get(lesson_id)
        for row in read_jsonl(path)[:2]:
            ex = lesson.example(row["seed"], language=code)
            if ex.prompt != row["prompt"]:
                stale.append(lesson_id)
                break
    assert not stale, f"{code}: {len(stale)} lessons stale: {stale[:6]}"


@pytest.mark.parametrize("lesson_id", sorted(lc.lesson_ids(implemented_only=True))[::4])
def test_a_seed_gives_the_same_episode_in_any_process(lesson_id):
    """``example`` promises it, and one lesson was not keeping the promise.

    ``contradiction_tolerance`` built its candidate list by iterating the set
    a closure returned. A set of strings orders itself by hash, Python salts
    string hashing per process, and ``rng.choice`` over the result therefore
    picked a different atom in every run — so the same seed gave a different
    episode each time the samples were rebuilt, and the committed files could
    never have matched.

    Run as a subprocess with a different hash seed, because within one process
    the ordering is fixed and nothing is visible.
    """
    import json
    import subprocess
    import sys

    script = (
        "import json,sys,langcurriculum as lc;"
        "print(json.dumps(lc.get(sys.argv[1]).example(0).prompt))"
    )
    outs = set()
    for seed in ("1", "9"):
        proc = subprocess.run([sys.executable, "-c", script, lesson_id],
                              capture_output=True, text=True,
                              env={**os.environ, "PYTHONHASHSEED": seed})
        assert proc.returncode == 0, proc.stderr[-400:]
        outs.add(json.loads(proc.stdout))
    assert len(outs) == 1, f"{lesson_id} differs between processes"
