"""Compositional semantics and logical language."""

from __future__ import annotations

from .predicate_logic import PredicateLogic
from .quantification import Quantification
from .scope_ambiguity import ScopeAmbiguity
from .compositional_reference import CompositionalReference
from .spatial_language import SpatialLanguage
from .temporal_language import TemporalLanguage
from .event_semantics import EventSemantics
from .thematic_roles import ThematicRoles

SECTION = "ii"
SECTION_TITLE = "compositional semantics and logical language"

LESSONS = (
    PredicateLogic,
    Quantification,
    ScopeAmbiguity,
    CompositionalReference,
    SpatialLanguage,
    TemporalLanguage,
    EventSemantics,
    ThematicRoles,
)

__all__ = ["PredicateLogic", "Quantification", "ScopeAmbiguity", "CompositionalReference", "SpatialLanguage", "TemporalLanguage", "EventSemantics", "ThematicRoles", "LESSONS", "SECTION", "SECTION_TITLE"]
