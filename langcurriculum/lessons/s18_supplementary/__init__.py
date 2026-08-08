"""Supplementary syntax and semantics."""

from __future__ import annotations

from .center_embedding import CenterEmbedding
from .comparatives import Comparatives
from .counting_quantifier import CountingQuantifier
from .expression_eval import ExpressionEval
from .long_range_agreement import LongRangeAgreement
from .negation import Negation
from .nesting_depth_compare import NestingDepthCompare
from .palindrome import Palindrome
from .set_operations import SetOperations
from .string_reversal import StringReversal

SECTION = "supplementary"
SECTION_TITLE = "supplementary syntax and semantics"

LESSONS = (
    CenterEmbedding,
    Comparatives,
    CountingQuantifier,
    ExpressionEval,
    LongRangeAgreement,
    Negation,
    NestingDepthCompare,
    Palindrome,
    SetOperations,
    StringReversal,
)

__all__ = ["CenterEmbedding", "Comparatives", "CountingQuantifier", "ExpressionEval", "LongRangeAgreement", "Negation", "NestingDepthCompare", "Palindrome", "SetOperations", "StringReversal", "LESSONS", "SECTION", "SECTION_TITLE"]
