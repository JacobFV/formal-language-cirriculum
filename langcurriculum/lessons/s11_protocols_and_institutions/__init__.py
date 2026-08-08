"""Protocols, institutions, and distributed intelligence."""

from __future__ import annotations

from .protocol_discovery import ProtocolDiscovery
from .institution_learning import InstitutionLearning
from .institution_design import InstitutionDesign
from .norm_reasoning import NormReasoning
from .contract_reasoning import ContractReasoning
from .mechanism_design import MechanismDesign
from .coalition_formation import CoalitionFormation
from .distributed_knowledge import DistributedKnowledge
from .collective_theory_building import CollectiveTheoryBuilding
from .cultural_evolution import CulturalEvolution

SECTION = "xi"
SECTION_TITLE = "protocols, institutions, and distributed intelligence"

LESSONS = (
    ProtocolDiscovery,
    InstitutionLearning,
    InstitutionDesign,
    NormReasoning,
    ContractReasoning,
    MechanismDesign,
    CoalitionFormation,
    DistributedKnowledge,
    CollectiveTheoryBuilding,
    CulturalEvolution,
)

__all__ = ["ProtocolDiscovery", "InstitutionLearning", "InstitutionDesign", "NormReasoning", "ContractReasoning", "MechanismDesign", "CoalitionFormation", "DistributedKnowledge", "CollectiveTheoryBuilding", "CulturalEvolution", "LESSONS", "SECTION", "SECTION_TITLE"]
