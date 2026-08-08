"""Language as action."""

from __future__ import annotations

from .instruction_following_micro import InstructionFollowingMicro
from .instruction_composition import InstructionComposition
from .pronoun_coreference import PronounCoreference
from .discourse_state import DiscourseState
from .ellipsis import Ellipsis
from .presupposition import Presupposition
from .implicature import Implicature
from .speaker_listener_game import SpeakerListenerGame
from .lexicon_induction import LexiconInduction
from .grammar_induction import GrammarInduction
from .few_shot_language_learning import FewShotLanguageLearning
from .translation import Translation
from .paraphrase import Paraphrase
from .entailment import Entailment
from .knowledge_update import KnowledgeUpdate
from .belief_state import BeliefState
from .question_answering import QuestionAnswering
from .question_generation import QuestionGeneration
from .interactive_reference import InteractiveReference
from .definitions import Definitions
from .concept_invention import ConceptInvention

SECTION = "iii"
SECTION_TITLE = "language as action"

LESSONS = (
    InstructionFollowingMicro,
    InstructionComposition,
    PronounCoreference,
    DiscourseState,
    Ellipsis,
    Presupposition,
    Implicature,
    SpeakerListenerGame,
    LexiconInduction,
    GrammarInduction,
    FewShotLanguageLearning,
    Translation,
    Paraphrase,
    Entailment,
    KnowledgeUpdate,
    BeliefState,
    QuestionAnswering,
    QuestionGeneration,
    InteractiveReference,
    Definitions,
    ConceptInvention,
)

__all__ = ["InstructionFollowingMicro", "InstructionComposition", "PronounCoreference", "DiscourseState", "Ellipsis", "Presupposition", "Implicature", "SpeakerListenerGame", "LexiconInduction", "GrammarInduction", "FewShotLanguageLearning", "Translation", "Paraphrase", "Entailment", "KnowledgeUpdate", "BeliefState", "QuestionAnswering", "QuestionGeneration", "InteractiveReference", "Definitions", "ConceptInvention", "LESSONS", "SECTION", "SECTION_TITLE"]
