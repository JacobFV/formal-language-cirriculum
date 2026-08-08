"""Open-ended epistemology."""

from __future__ import annotations

from .open_ended_concept_discovery import OpenEndedConceptDiscovery
from .open_ended_question_generation import OpenEndedQuestionGeneration
from .research_program import ResearchProgram
from .paradigm_shift import ParadigmShift
from .world_model_synthesis import WorldModelSynthesis
from .cross_domain_unification import CrossDomainUnification
from .theory_transfer import TheoryTransfer
from .formalization import Formalization
from .deformalization import Deformalization
from .ambiguity_preservation import AmbiguityPreservation
from .underspecification_reasoning import UnderspecificationReasoning

SECTION = "xiv"
SECTION_TITLE = "open-ended epistemology"

LESSONS = (
    OpenEndedConceptDiscovery,
    OpenEndedQuestionGeneration,
    ResearchProgram,
    ParadigmShift,
    WorldModelSynthesis,
    CrossDomainUnification,
    TheoryTransfer,
    Formalization,
    Deformalization,
    AmbiguityPreservation,
    UnderspecificationReasoning,
)

__all__ = ["OpenEndedConceptDiscovery", "OpenEndedQuestionGeneration", "ResearchProgram", "ParadigmShift", "WorldModelSynthesis", "CrossDomainUnification", "TheoryTransfer", "Formalization", "Deformalization", "AmbiguityPreservation", "UnderspecificationReasoning", "LESSONS", "SECTION", "SECTION_TITLE"]
