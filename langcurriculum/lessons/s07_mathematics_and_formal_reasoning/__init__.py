"""Mathematics and formal reasoning."""

from __future__ import annotations

from .mathematical_definition_learning import MathematicalDefinitionLearning
from .conjecture_generation import ConjectureGeneration
from .theorem_proving import TheoremProving
from .lemma_invention import LemmaInvention
from .proof_compression import ProofCompression
from .proof_translation import ProofTranslation
from .counterexample_generation import CounterexampleGeneration
from .logic_discovery import LogicDiscovery
from .logic_selection import LogicSelection
from .uncertain_symbolic_reasoning import UncertainSymbolicReasoning
from .default_reasoning import DefaultReasoning
from .belief_revision import BeliefRevision
from .contradiction_tolerance import ContradictionTolerance

SECTION = "vii"
SECTION_TITLE = "mathematics and formal reasoning"

LESSONS = (
    MathematicalDefinitionLearning,
    ConjectureGeneration,
    TheoremProving,
    LemmaInvention,
    ProofCompression,
    ProofTranslation,
    CounterexampleGeneration,
    LogicDiscovery,
    LogicSelection,
    UncertainSymbolicReasoning,
    DefaultReasoning,
    BeliefRevision,
    ContradictionTolerance,
)

__all__ = ["MathematicalDefinitionLearning", "ConjectureGeneration", "TheoremProving", "LemmaInvention", "ProofCompression", "ProofTranslation", "CounterexampleGeneration", "LogicDiscovery", "LogicSelection", "UncertainSymbolicReasoning", "DefaultReasoning", "BeliefRevision", "ContradictionTolerance", "LESSONS", "SECTION", "SECTION_TITLE"]
