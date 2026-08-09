"""The concrete grammars, and the registry that finds them.

Each module here is one language expressed as parameters plus the overrides its
typology genuinely needs. The count of overrides is the honest measure of
whether the engine is doing its job, so it is worth stating:

======================  ==========  ===========================================
grammar                 overrides   what they are
======================  ==========  ===========================================
:mod:`.english`         2           a/an phonology; auxiliary fronting
:mod:`.turkish`         4           mI clitic; possession; locative case; DOM
:mod:`.swahili`         3           class concord prefixes; verb agreement;
                                    the class-pair plural
======================  ==========  ===========================================

If a grammar starts needing a dozen overrides, that is evidence the
parameterization in :mod:`~langcurriculum.grammar.linearize` is missing an axis,
not that the language is unusual.
"""

from __future__ import annotations

from ..linearize import Grammar
from ..registry import REGISTRY
from .chinese import Chinese
from .english import English, EnglishSynonym
from .spanish import Spanish
from .swahili import Swahili
from .turkish import Turkish

__all__ = ["GRAMMARS", "get_grammar", "register_grammar", "grammar_codes",
           "English", "EnglishSynonym", "Spanish", "Chinese", "Turkish",
           "Swahili", "HANDWRITTEN"]

#: The hand-written grammars, by the code the curriculum has always used, and
#: by ISO 639-3 so that they shadow the derived grammar for the same language.
#: A verified grammar must always win over a generated one for its own language.
HANDWRITTEN: dict[str, type[Grammar]] = {
    "english": English, "spanish": Spanish, "chinese": Chinese,
    "turkish": Turkish, "swahili": Swahili,
    "english_synonym": EnglishSynonym,
}
_ISO = {"english": "eng", "spanish": "spa", "chinese": "cmn",
        "turkish": "tur", "swahili": "swh"}

GRAMMARS: dict[str, Grammar] = {}


def register_grammar(grammar: Grammar) -> Grammar:
    if not grammar.code:
        raise ValueError("a grammar needs a code")
    GRAMMARS[grammar.code] = grammar
    REGISTRY.register(grammar)
    iso = _ISO.get(grammar.code)
    if iso and iso != grammar.code:
        REGISTRY._handwritten[iso] = grammar
        REGISTRY._available = None
    return grammar


def get_grammar(code: str) -> Grammar:
    key = (code or "").strip().lower()
    if key in GRAMMARS:
        return GRAMMARS[key]
    return REGISTRY.get(key)


def grammar_codes() -> list[str]:
    return sorted(GRAMMARS)


for _cls in (English, Spanish, Chinese, Turkish, Swahili, EnglishSynonym):
    register_grammar(_cls())
