"""Civilization-scale symbolic learning."""

from __future__ import annotations

from .civilization_simulator import CivilizationSimulator
from .scientific_civilization import ScientificCivilization
from .symbolic_world_builder import SymbolicWorldBuilder
from .curriculum_invention import CurriculumInvention

SECTION = "xvi"
SECTION_TITLE = "civilization-scale symbolic learning"

LESSONS = (
    CivilizationSimulator,
    ScientificCivilization,
    SymbolicWorldBuilder,
    CurriculumInvention,
)

__all__ = ["CivilizationSimulator", "ScientificCivilization", "SymbolicWorldBuilder", "CurriculumInvention", "LESSONS", "SECTION", "SECTION_TITLE"]
