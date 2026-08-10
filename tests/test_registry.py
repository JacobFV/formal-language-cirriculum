"""The registry is a claim about coverage. These tests hold it to it."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import langcurriculum as lc
from langcurriculum.lessons import LESSON_CLASSES

ROOT = Path(__file__).resolve().parent.parent
LESSON_DIR = ROOT / "langcurriculum" / "lessons"


def test_counts_match_the_advertised_numbers():
    assert len(lc.REGISTRY) == lc.N_REGISTERED == 180
    assert len(lc.curriculum("core170")) == lc.N_NUMBERED == 170
    assert len(lc.curriculum("supplementary")) == 10


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
        assert lesson.tags, lesson.id
        assert all(isinstance(t, str) and t for t in lesson.tags), lesson.id
        assert lesson.level >= 0, lesson.id
        assert set(lesson.axes) <= set(lc.AXES), lesson.id
        assert set(lesson.axes) & set(lc.CORE_AXES), lesson.id
        assert all(isinstance(v, int) for v in lesson.axes.values()), lesson.id
        assert isinstance(lesson.capabilities, tuple), lesson.id


def test_a_lesson_declares_nothing_about_its_position():
    """Ordering is a curriculum's opinion, so a lesson must not carry one.

    This is the invariant the flattening exists to establish: if a number or a
    section creeps back onto a lesson class, two sources of truth about ordering
    exist again and they will disagree.
    """
    for cls in LESSON_CLASSES:
        for banned in ("number", "section", "section_title"):
            assert not hasattr(cls, banned), f"{cls.id} declares {banned}"


def test_one_module_and_one_class_per_lesson():
    seen_modules = set()
    for cls in LESSON_CLASSES:
        mod = inspect.getmodule(cls)
        assert mod is not None
        path = Path(mod.__file__ or "")
        assert path.stem == cls.id, f"{cls.__name__} lives in {path.name}"
        assert path.parent == LESSON_DIR, f"{cls.id} is not in the flat lessons directory"
        assert path not in seen_modules, f"two lessons in {path}"
        seen_modules.add(path)
    assert len(seen_modules) == len(LESSON_CLASSES)


def test_the_declared_imports_and_the_directory_agree():
    """No module silently skipped, and none silently unlisted.

    The registry is written out rather than scanned so that a module which fails
    to import is a loud error. That only helps if the two sets are checked
    against each other, which is what this does.
    """
    on_disk = {p.stem for p in LESSON_DIR.glob("*.py") if p.stem != "__init__"}
    declared = {c.id for c in LESSON_CLASSES}
    assert on_disk == declared


def test_get_rejects_an_unknown_id():
    with pytest.raises(KeyError):
        lc.get("no_such_lesson")


def test_resolve_accepts_ids_curricula_tags_and_none():
    assert len(lc.resolve(None)) == 179            # every implemented lesson
    assert [l.id for l in lc.resolve("unification,quantification")] == \
        ["unification", "quantification"]
    assert len(lc.resolve("core170")) == 169       # the spec-only lesson is numbered
    assert len(lc.resolve("curriculum:supplementary")) == 10
    maths = lc.resolve("tag:mathematics")
    assert maths and all("mathematics" in l.tags for l in maths)


def test_capability_index_is_non_empty_and_consistent():
    index = lc.by_capability()
    assert len(index) > 100
    for cap, ids in index.items():
        for i in ids:
            assert cap in lc.get(i).capabilities


def test_the_tag_index_covers_every_lesson():
    index = lc.by_tag()
    assert set().union(*index.values()) == set(lc.REGISTRY)
    for tag, ids in index.items():
        for i in ids:
            assert tag in lc.get(i).tags


def test_flattening_preserved_the_order_the_package_used_to_have():
    """The one test that makes the reorganization provably lossless.

    ``_frozen_order.json`` was captured from ``LESSON_CLASSES`` immediately
    before the lessons were flattened, when order came from the section packages.
    Reproducing it from the curricula shows that nothing was reordered, dropped
    or duplicated on the way.
    """
    frozen = json.loads((Path(__file__).parent / "_frozen_order.json").read_text())["order"]
    rebuilt = ([n.lesson for n in lc.curriculum("core170").linearize()]
               + [n.lesson for n in lc.curriculum("supplementary").linearize()])
    assert rebuilt == frozen


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
