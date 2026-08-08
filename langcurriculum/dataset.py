"""Emitting the curriculum as data: JSONL anyone can train on.

The generators are the asset; a file is just one crystallization of them. Export
as much as you want, from whichever seed range you want, and the only thing you
have to keep straight is that **train and evaluation seeds must not overlap**.
:func:`splits` does that for you.

One record per episode::

    {"lesson_id": ..., "seed": ..., "language": ...,
     "prompt": ..., "answer": ..., "choices": [...],
     "observation": ..., "metadata": {...}}

``prompt``/``answer`` is the pair most training pipelines want. ``observation``
is the question without the answer-set instruction, for callers who prefer to
format it themselves. ``metadata`` carries the lesson's level, section, axes and
the episode's hidden ground truth — useful for analysis, and the one field you
must not feed to a model you intend to then evaluate.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .languages import DEFAULT_LANGUAGE
from .registry import resolve

__all__ = ["iter_records", "write_jsonl", "read_jsonl", "splits", "export"]


def _shape(rec: dict[str, Any], *, include_hidden: bool, include_observation: bool) -> dict[str, Any]:
    if not include_hidden:
        rec["metadata"] = {k: v for k, v in rec["metadata"].items() if k != "hidden"}
    if not include_observation:
        rec.pop("observation", None)
    return rec


def iter_records(lessons: str | Sequence[str] | None = None, *, n: int = 100,
                 seed0: int = 0, language: str = DEFAULT_LANGUAGE, include_hidden: bool = True,
                 include_observation: bool = True) -> Iterator[dict[str, Any]]:
    """Generate ``n`` episodes per lesson as plain dicts.

    ``observation`` is the prompt without its trailing answer-set instruction;
    dropping it roughly halves the bytes and loses nothing you cannot rebuild.
    """
    for lesson in resolve(lessons):
        if lesson.status != "implemented":
            continue
        for ex in lesson.examples(n, seed0=seed0, language=language):
            yield _shape(ex.to_dict(), include_hidden=include_hidden,
                         include_observation=include_observation)


def write_jsonl(path: str | os.PathLike[str], records: Iterable[dict[str, Any]]) -> int:
    """Write records to a JSONL file, creating parent directories. Returns the count."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def read_jsonl(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """Read a JSONL file back into dicts."""
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def export(path: str | os.PathLike[str], lessons: str | Sequence[str] | None = None, *,
           n: int = 100, seed0: int = 0, language: str = DEFAULT_LANGUAGE,
           include_hidden: bool = True, include_observation: bool = True,
           per_lesson: bool = False) -> int:
    """Export a dataset.

    With ``per_lesson=False`` (the default) everything goes into one JSONL file
    at ``path``. With ``per_lesson=True``, ``path`` is a directory and each
    lesson gets ``<lesson_id>.jsonl``, which is what the committed sample set
    under ``data/samples/`` looks like.
    """
    if not per_lesson:
        return write_jsonl(path, iter_records(lessons, n=n, seed0=seed0, language=language,
                                              include_hidden=include_hidden,
                                              include_observation=include_observation))
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    total = 0
    for lesson in resolve(lessons):
        if lesson.status != "implemented":
            continue
        recs = (_shape(ex.to_dict(), include_hidden=include_hidden,
                       include_observation=include_observation)
                for ex in lesson.examples(n, seed0=seed0, language=language))
        total += write_jsonl(root / f"{lesson.id}.jsonl", recs)
    return total


def splits(train: int = 1000, eval: int = 200, *, gap: int = 1_000_000) -> dict[str, tuple[int, int]]:
    """Disjoint seed ranges, as ``{"train": (seed0, n), "eval": (seed0, n)}``.

    Disjointness here is by construction rather than by sampling: the two ranges
    cannot overlap, so an evaluation episode is a world the training set could
    not have contained.
    """
    return {"train": (0, train), "eval": (gap, eval)}
