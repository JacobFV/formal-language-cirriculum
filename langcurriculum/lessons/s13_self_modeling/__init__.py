"""Self-modeling and architecture adaptation."""

from __future__ import annotations

from .self_model import SelfModel
from .capability_estimation import CapabilityEstimation
from .self_error_diagnosis import SelfErrorDiagnosis
from .self_repair import SelfRepair
from .architecture_selection import ArchitectureSelection
from .architecture_composition import ArchitectureComposition
from .tool_construction import ToolConstruction
from .external_memory_design import ExternalMemoryDesign
from .knowledge_refactoring import KnowledgeRefactoring
from .semantic_compression import SemanticCompression
from .minimum_description_learning import MinimumDescriptionLearning

SECTION = "xiii"
SECTION_TITLE = "self-modeling and architecture adaptation"

LESSONS = (
    SelfModel,
    CapabilityEstimation,
    SelfErrorDiagnosis,
    SelfRepair,
    ArchitectureSelection,
    ArchitectureComposition,
    ToolConstruction,
    ExternalMemoryDesign,
    KnowledgeRefactoring,
    SemanticCompression,
    MinimumDescriptionLearning,
)

__all__ = ["SelfModel", "CapabilityEstimation", "SelfErrorDiagnosis", "SelfRepair", "ArchitectureSelection", "ArchitectureComposition", "ToolConstruction", "ExternalMemoryDesign", "KnowledgeRefactoring", "SemanticCompression", "MinimumDescriptionLearning", "LESSONS", "SECTION", "SECTION_TITLE"]
