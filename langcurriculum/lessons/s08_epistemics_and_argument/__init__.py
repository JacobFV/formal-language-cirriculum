"""Epistemics, argument, and teaching."""

from __future__ import annotations

from .source_provenance import SourceProvenance
from .source_reliability_learning import SourceReliabilityLearning
from .argumentation import Argumentation
from .adversarial_argumentation import AdversarialArgumentation
from .explanation import Explanation
from .explanation_repair import ExplanationRepair
from .teaching import Teaching
from .curriculum_design import CurriculumDesign
from .knowledge_gap_detection import KnowledgeGapDetection

SECTION = "viii"
SECTION_TITLE = "epistemics, argument, and teaching"

LESSONS = (
    SourceProvenance,
    SourceReliabilityLearning,
    Argumentation,
    AdversarialArgumentation,
    Explanation,
    ExplanationRepair,
    Teaching,
    CurriculumDesign,
    KnowledgeGapDetection,
)

__all__ = ["SourceProvenance", "SourceReliabilityLearning", "Argumentation", "AdversarialArgumentation", "Explanation", "ExplanationRepair", "Teaching", "CurriculumDesign", "KnowledgeGapDetection", "LESSONS", "SECTION", "SECTION_TITLE"]
