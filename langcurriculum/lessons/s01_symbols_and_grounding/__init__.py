"""Symbols, grounding, and elementary language."""

from __future__ import annotations

from .symbol_grounding import SymbolGrounding
from .symbol_equivalence import SymbolEquivalence
from .symbol_discrimination import SymbolDiscrimination
from .sequence_copy import SequenceCopy
from .next_symbol import NextSymbol
from .finite_state_language import FiniteStateLanguage
from .context_free_language import ContextFreeLanguage
from .parse_depth import ParseDepth
from .tree_to_sequence import TreeToSequence
from .variable_binding import VariableBinding
from .unification import Unification

SECTION = "i"
SECTION_TITLE = "symbols, grounding, and elementary language"

LESSONS = (
    SymbolGrounding,
    SymbolEquivalence,
    SymbolDiscrimination,
    SequenceCopy,
    NextSymbol,
    FiniteStateLanguage,
    ContextFreeLanguage,
    ParseDepth,
    TreeToSequence,
    VariableBinding,
    Unification,
)

__all__ = ["SymbolGrounding", "SymbolEquivalence", "SymbolDiscrimination", "SequenceCopy", "NextSymbol", "FiniteStateLanguage", "ContextFreeLanguage", "ParseDepth", "TreeToSequence", "VariableBinding", "Unification", "LESSONS", "SECTION", "SECTION_TITLE"]
