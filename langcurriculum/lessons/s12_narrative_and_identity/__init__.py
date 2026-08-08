"""History, narrative, perspective, and identity."""

from __future__ import annotations

from .historical_reconstruction import HistoricalReconstruction
from .narrative_modeling import NarrativeModeling
from .multi_perspective_modeling import MultiPerspectiveModeling
from .identity_continuity import IdentityContinuity

SECTION = "xii"
SECTION_TITLE = "history, narrative, perspective, and identity"

LESSONS = (
    HistoricalReconstruction,
    NarrativeModeling,
    MultiPerspectiveModeling,
    IdentityContinuity,
)

__all__ = ["HistoricalReconstruction", "NarrativeModeling", "MultiPerspectiveModeling", "IdentityContinuity", "LESSONS", "SECTION", "SECTION_TITLE"]
