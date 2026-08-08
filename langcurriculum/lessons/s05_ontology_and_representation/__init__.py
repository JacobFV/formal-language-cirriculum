"""Ontology and representation."""

from __future__ import annotations

from .ontology_construction import OntologyConstruction
from .ontology_revision import OntologyRevision
from .ontology_alignment import OntologyAlignment
from .representation_selection import RepresentationSelection
from .representation_invention import RepresentationInvention
from .abstraction_ladder import AbstractionLadder
from .conceptual_chunking import ConceptualChunking

SECTION = "v"
SECTION_TITLE = "ontology and representation"

LESSONS = (
    OntologyConstruction,
    OntologyRevision,
    OntologyAlignment,
    RepresentationSelection,
    RepresentationInvention,
    AbstractionLadder,
    ConceptualChunking,
)

__all__ = ["OntologyConstruction", "OntologyRevision", "OntologyAlignment", "RepresentationSelection", "RepresentationInvention", "AbstractionLadder", "ConceptualChunking", "LESSONS", "SECTION", "SECTION_TITLE"]
