"""Problem formulation and hierarchical agency."""

from __future__ import annotations

from .problem_formulation import ProblemFormulation
from .problem_reformulation import ProblemReformulation
from .decomposition import Decomposition
from .hierarchical_planning import HierarchicalPlanning
from .long_horizon_projects import LongHorizonProjects
from .resource_bounded_reasoning import ResourceBoundedReasoning
from .anytime_reasoning import AnytimeReasoning
from .metareasoning import Metareasoning
from .strategy_discovery import StrategyDiscovery
from .strategy_transfer import StrategyTransfer
from .algorithm_discovery import AlgorithmDiscovery
from .algorithm_analysis import AlgorithmAnalysis

SECTION = "ix"
SECTION_TITLE = "problem formulation and hierarchical agency"

LESSONS = (
    ProblemFormulation,
    ProblemReformulation,
    Decomposition,
    HierarchicalPlanning,
    LongHorizonProjects,
    ResourceBoundedReasoning,
    AnytimeReasoning,
    Metareasoning,
    StrategyDiscovery,
    StrategyTransfer,
    AlgorithmDiscovery,
    AlgorithmAnalysis,
)

__all__ = ["ProblemFormulation", "ProblemReformulation", "Decomposition", "HierarchicalPlanning", "LongHorizonProjects", "ResourceBoundedReasoning", "AnytimeReasoning", "Metareasoning", "StrategyDiscovery", "StrategyTransfer", "AlgorithmDiscovery", "AlgorithmAnalysis", "LESSONS", "SECTION", "SECTION_TITLE"]
