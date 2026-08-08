"""The registry is a claim about coverage. These tests hold it to it."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import langcurriculum as lc
from langcurriculum.lessons import LESSON_CLASSES, SECTIONS

ROOT = Path(__file__).resolve().parent.parent


def test_counts_match_the_advertised_numbers():
    assert len(lc.REGISTRY) == lc.N_REGISTERED == 180
    assert len(lc.numbered()) == lc.N_NUMBERED == 170
    assert len(lc.supplementary()) == 10


def test_the_numbered_curriculum_is_exactly_1_to_170_with_no_gaps():
    numbers = sorted(l.number for l in lc.numbered())
    assert numbers == list(range(1, 171))


def test_every_lesson_id_is_unique_and_a_valid_identifier():
    ids = [c.id for c in LESSON_CLASSES]
    assert len(set(ids)) == len(ids)
    assert all(i.isidentifier() and i.islower() for i in ids)


def test_exactly_one_lesson_is_spec_only():
    spec = [l for l in lc.all_lessons().values() if l.status == "spec"]
    assert [l.id for l in spec] == ["open_world_research_agent"]
    assert spec[0].note, "a spec-only lesson must say why"


def test_every_lesson_declares_its_metadata():
    for lesson in lc.all_lessons().values():
        assert lesson.teaches, lesson.id
        assert lesson.section in lc.SECTION_TITLES, lesson.id
        assert lesson.section_title, lesson.id
        assert lesson.level >= 0, lesson.id
        assert set(lesson.axes) <= set(lc.AXES), lesson.id
        assert set(lesson.axes) & set(lc.CORE_AXES), lesson.id
        assert all(isinstance(v, int) for v in lesson.axes.values()), lesson.id
        assert isinstance(lesson.capabilities, tuple), lesson.id


def test_one_module_and_one_class_per_lesson():
    seen_modules = set()
    for cls in LESSON_CLASSES:
        mod = inspect.getmodule(cls)
        assert mod is not None
        path = Path(mod.__file__ or "")
        assert path.stem == cls.id, f"{cls.__name__} lives in {path.name}"
        assert path not in seen_modules, f"two lessons in {path}"
        seen_modules.add(path)
    assert len(seen_modules) == len(LESSON_CLASSES)


def test_sections_partition_the_registry():
    from_sections = [c.id for s in SECTIONS for c in s.LESSONS]
    assert sorted(from_sections) == sorted(lc.REGISTRY)
    assert len(SECTIONS) == 18            # 17 numbered sections + supplementary
    for s in lc.sections():
        assert s["lessons"], s["section"]
        assert all(lc.get(i).section == s["section"] for i in s["lessons"])


def test_get_rejects_an_unknown_id():
    with pytest.raises(KeyError):
        lc.get("no_such_lesson")


def test_resolve_accepts_ids_sections_and_none():
    assert len(lc.resolve(None)) == 179            # every implemented lesson
    assert len(lc.resolve("vii")) == 13
    assert [l.id for l in lc.resolve("unification,quantification")] == \
        ["unification", "quantification"]


def test_capability_index_is_non_empty_and_consistent():
    index = lc.by_capability()
    assert len(index) > 100
    for cap, ids in index.items():
        for i in ids:
            assert cap in lc.get(i).capabilities


def test_nothing_imports_a_host_framework():
    """The package must stand alone: no import outside itself and the stdlib.

    Parsed rather than grepped, so a line inside a docstring — the worked
    example of registering a language, for instance — is not mistaken for one.
    """
    import ast
    import sys

    stdlib = set(sys.stdlib_module_names)
    for path in (ROOT / "langcurriculum").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level > 0:                    # relative: our own package
                    continue
                top = (node.module or "").split(".")[0]
            elif isinstance(node, ast.Import):
                top = node.names[0].name.split(".")[0]
            else:
                continue
            assert top in stdlib or top == "__future__", f"{path}: imports {top}"
