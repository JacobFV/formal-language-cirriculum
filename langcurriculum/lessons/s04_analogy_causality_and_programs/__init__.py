"""Analogy, causality, planning, and programs."""

from __future__ import annotations

from .analogy import Analogy
from .causal_language import CausalLanguage
from .counterfactuals import Counterfactuals
from .planning_language import PlanningLanguage
from .procedural_language import ProceduralLanguage
from .program_synthesis import ProgramSynthesis
from .program_explanation import ProgramExplanation
from .dialogue_game import DialogueGame
from .negotiation_game import NegotiationGame
from .deception_detection import DeceptionDetection
from .social_convention_learning import SocialConventionLearning
from .document_world import DocumentWorld
from .compressed_language import CompressedLanguage
from .noisy_channel_language import NoisyChannelLanguage
from .multimodal_symbolization import MultimodalSymbolization
from .open_world_language import OpenWorldLanguage
from .continual_language import ContinualLanguage
from .language_culture import LanguageCulture
from .general_language_agent import GeneralLanguageAgent
from .natural_language_bridge import NaturalLanguageBridge

SECTION = "iv"
SECTION_TITLE = "analogy, causality, planning, and programs"

LESSONS = (
    Analogy,
    CausalLanguage,
    Counterfactuals,
    PlanningLanguage,
    ProceduralLanguage,
    ProgramSynthesis,
    ProgramExplanation,
    DialogueGame,
    NegotiationGame,
    DeceptionDetection,
    SocialConventionLearning,
    DocumentWorld,
    CompressedLanguage,
    NoisyChannelLanguage,
    MultimodalSymbolization,
    OpenWorldLanguage,
    ContinualLanguage,
    LanguageCulture,
    GeneralLanguageAgent,
    NaturalLanguageBridge,
)

__all__ = ["Analogy", "CausalLanguage", "Counterfactuals", "PlanningLanguage", "ProceduralLanguage", "ProgramSynthesis", "ProgramExplanation", "DialogueGame", "NegotiationGame", "DeceptionDetection", "SocialConventionLearning", "DocumentWorld", "CompressedLanguage", "NoisyChannelLanguage", "MultimodalSymbolization", "OpenWorldLanguage", "ContinualLanguage", "LanguageCulture", "GeneralLanguageAgent", "NaturalLanguageBridge", "LESSONS", "SECTION", "SECTION_TITLE"]
