"""Scientific induction and model discovery."""

from __future__ import annotations

from .latent_rule_discovery import LatentRuleDiscovery
from .scientific_model_induction import ScientificModelInduction
from .experimental_design import ExperimentalDesign
from .theory_comparison import TheoryComparison
from .falsification import Falsification
from .anomaly_resolution import AnomalyResolution
from .mechanism_discovery import MechanismDiscovery
from .multiscale_modeling import MultiscaleModeling
from .emergence_discovery import EmergenceDiscovery
from .invariance_discovery import InvarianceDiscovery
from .symmetry_reasoning import SymmetryReasoning
from .conservation_law_discovery import ConservationLawDiscovery
from .dimensional_analysis import DimensionalAnalysis

SECTION = "vi"
SECTION_TITLE = "scientific induction and model discovery"

LESSONS = (
    LatentRuleDiscovery,
    ScientificModelInduction,
    ExperimentalDesign,
    TheoryComparison,
    Falsification,
    AnomalyResolution,
    MechanismDiscovery,
    MultiscaleModeling,
    EmergenceDiscovery,
    InvarianceDiscovery,
    SymmetryReasoning,
    ConservationLawDiscovery,
    DimensionalAnalysis,
)

__all__ = ["LatentRuleDiscovery", "ScientificModelInduction", "ExperimentalDesign", "TheoryComparison", "Falsification", "AnomalyResolution", "MechanismDiscovery", "MultiscaleModeling", "EmergenceDiscovery", "InvarianceDiscovery", "SymmetryReasoning", "ConservationLawDiscovery", "DimensionalAnalysis", "LESSONS", "SECTION", "SECTION_TITLE"]
