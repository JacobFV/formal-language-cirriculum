"""The registry: lesson id -> lesson class, and the ways of slicing it.

The registry is deliberately explicit. Every lesson class is imported by name
in :mod:`langcurriculum.lessons`, so what is in the curriculum is a fact you can
read off the source tree rather than the result of a directory scan that might
quietly skip a file that failed to import.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .lesson import Lesson
from .lessons import LESSON_CLASSES, SECTIONS

__all__ = ["REGISTRY", "SECTION_TITLES", "all_lessons", "get", "lesson_ids",
           "by_section", "by_capability", "sections", "numbered", "supplementary"]

#: lesson id -> the class implementing it
REGISTRY: Mapping[str, type[Lesson]] = {c.id: c for c in LESSON_CLASSES}

#: section key -> human-readable title, in curriculum order
SECTION_TITLES: Mapping[str, str] = {s.SECTION: s.SECTION_TITLE for s in SECTIONS}

_INSTANCES: dict[str, Lesson] = {}

if len(REGISTRY) != len(LESSON_CLASSES):  # pragma: no cover - guards a build mistake
    raise RuntimeError("duplicate lesson id in the registry")


def get(lesson_id: str) -> Lesson:
    """The lesson with this id, as a ready-to-use instance."""
    if lesson_id not in REGISTRY:
        raise KeyError(f"unknown lesson {lesson_id!r}; "
                       f"there are {len(REGISTRY)}, try lesson_ids()")
    inst = _INSTANCES.get(lesson_id)
    if inst is None:
        inst = _INSTANCES[lesson_id] = REGISTRY[lesson_id]()
    return inst


def all_lessons(*, implemented_only: bool = False) -> dict[str, Lesson]:
    """Every lesson, in curriculum order, id -> instance."""
    out = {c.id: get(c.id) for c in LESSON_CLASSES}
    if implemented_only:
        out = {k: v for k, v in out.items() if v.status == "implemented"}
    return out


def lesson_ids(*, implemented_only: bool = False) -> list[str]:
    return list(all_lessons(implemented_only=implemented_only))


def sections() -> list[dict[str, object]]:
    """One entry per section: key, title, and the lesson ids it contains."""
    return [{"section": s.SECTION, "title": s.SECTION_TITLE,
             "lessons": [c.id for c in s.LESSONS]} for s in SECTIONS]


def by_section(section: str) -> list[Lesson]:
    """Every lesson in a section, by its key (``"iv"``, ``"supplementary"``)."""
    return [get(c.id) for s in SECTIONS if s.SECTION == section for c in s.LESSONS]


def by_capability() -> dict[str, list[str]]:
    """capability tag -> the lessons that exercise it."""
    out: dict[str, list[str]] = {}
    for l in all_lessons().values():
        for c in l.capabilities:
            out.setdefault(c, []).append(l.id)
    return out


def numbered() -> list[Lesson]:
    """The 170 lessons of the numbered curriculum, in order."""
    return sorted((l for l in all_lessons().values() if l.number is not None),
                  key=lambda l: l.number or 0)


def supplementary() -> list[Lesson]:
    """The lessons outside the numbered sequence."""
    return [l for l in all_lessons().values() if l.number is None]


def resolve(spec: str | Sequence[str] | None) -> list[Lesson]:
    """Turn a selector into lessons.

    ``None`` or ``"all"`` means every implemented lesson; a section key means
    that section; otherwise a comma-separated list of lesson ids.
    """
    if spec is None or spec in ("all", ""):
        return list(all_lessons(implemented_only=True).values())
    if isinstance(spec, str):
        if spec in SECTION_TITLES:
            return [l for l in by_section(spec) if l.status == "implemented"]
        names = [s.strip() for s in spec.split(",") if s.strip()]
    else:
        names = list(spec)
    return [get(n) for n in names]
