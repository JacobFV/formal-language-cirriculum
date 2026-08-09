"""The concrete grammars, and the registry that finds them.

Each module here is one language expressed as parameters plus the overrides its
typology genuinely needs, and the count of overrides is the honest measure of
whether the parameterization is doing its job. Counted from the source rather
than remembered:

======================  ==========  ===========================================
grammar                 overrides   what they are
======================  ==========  ===========================================
:mod:`.spanish`         5           gendered articles with the el-agua
                                    exception, y/e and o/u, ser vs estar, a
                                    label's trailing preposition
:mod:`.english`         4           a/an phonology, and negation, polar
                                    questions and wh-questions all attaching to
                                    a finite auxiliary
:mod:`.turkish`         6           the mI clitic, evidentiality, double-marked
                                    possession, locative case, differential
                                    object marking
:mod:`.swahili`         3           class concord prefixes, the class-pair
                                    plural, the nasal allomorph
:mod:`.chinese`         11          measure words, per-adjective 的,
                                    topic-comment framing, 吗 and 还是
                                    questions, and its own typography
======================  ==========  ===========================================

Chinese is the one worth staring at. Several of its eleven are real — a measure
word is not a determiner and no parameter will make it one — but ``join_list``,
``sentence`` and ``block_heading`` are there because the typography of a
script written without spaces is still partly hard-coded in the walk rather
than read off :class:`~langcurriculum.grammar.linearize.Typography`. That is a
gap in the parameterization and is recorded here rather than rounded down.
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
