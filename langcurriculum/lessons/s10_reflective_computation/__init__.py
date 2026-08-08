"""Reflective computation and language design."""

from __future__ import annotations

from .recursive_self_application import RecursiveSelfApplication
from .metalinguistic_reasoning import MetalinguisticReasoning
from .language_design import LanguageDesign
from .dsl_invention import DslInvention
from .compiler_construction import CompilerConstruction
from .interpreter_learning import InterpreterLearning

SECTION = "x"
SECTION_TITLE = "reflective computation and language design"

LESSONS = (
    RecursiveSelfApplication,
    MetalinguisticReasoning,
    LanguageDesign,
    DslInvention,
    CompilerConstruction,
    InterpreterLearning,
)

__all__ = ["RecursiveSelfApplication", "MetalinguisticReasoning", "LanguageDesign", "DslInvention", "CompilerConstruction", "InterpreterLearning", "LESSONS", "SECTION", "SECTION_TITLE"]
