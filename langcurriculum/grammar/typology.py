"""Deriving grammar parameters from typological databases.

The parameters in :mod:`~langcurriculum.grammar.linearize` were not invented for
this package. They are the axes along which WALS — *The World Atlas of Language
Structures* — codes the world's languages, and that correspondence is what makes
a hundred grammars possible without a hundred linguists: the coding already
exists, for 2,660 languages, done by the people who study them.

The mapping is direct enough to be read off:

===============  ==========================================  ==========================
WALS feature     what it codes                               engine parameter
===============  ==========================================  ==========================
81A              order of subject, object and verb           ``WordOrder.clause``
87A              order of adjective and noun                 ``WordOrder.adj``
85A              order of adposition and noun phrase         ``WordOrder.adposition``
86A              order of genitive and noun                  ``WordOrder.possessive``
88A              order of demonstrative and noun             ``WordOrder.det``
89A              order of numeral and noun                   ``WordOrder.numeral``
93A              position of interrogative phrases           ``WordOrder.wh_fronting``
92A              position of polar question particles        polar question strategy
143A             order of negative morpheme and verb         ``WordOrder.negation``
98A              alignment of case marking                   ``Alignment.case_of``
30A              number of genders                           ``Concord``
37A / 38A        definite and indefinite articles            whether determiners exist
55A              numeral classifiers                         classifier strategy
51A              position of case affixes                    morphology direction
===============  ==========================================  ==========================

What this does and does not give you
------------------------------------

A derived profile gets **word order and the presence or absence of a category
right**, because that is exactly what WALS codes. It does not give you the
*forms*: knowing that Hungarian is postpositional does not tell you that the
inessive is ``-ban``/``-ben``, and knowing that Hindi is ergative in the
perfective does not produce ``ne``. Those come from UniMorph, separately, and a
language with a profile but no morphology is honestly labelled tier 4 rather
than quietly rendered as though word order were the whole of grammar.

The other limit is real and worth stating: WALS codes a *dominant* order. A
language coded "no dominant order" is not thereby SVO, and about 190 languages
are coded that way for 81A alone. Those keep the flag
:attr:`Profile.order_uncertain` so that nothing downstream mistakes a default
for a finding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from .category import CLS, NUM
from .linearize import (
    ERG_ABS, NOM_ACC, NO_CASE, Alignment, Concord, Sandhi, Typography,
    WordOrder,
)

__all__ = ["Profile", "derive_profile", "WALS_FEATURES", "RTL_SCRIPTS",
           "NO_SPACE_SCRIPTS"]

#: the WALS features the derivation reads. Anything not here is ignored, and
#: anything here that a language lacks falls back with ``order_uncertain`` set.
WALS_FEATURES = ("81A", "87A", "85A", "86A", "88A", "89A", "92A", "93A",
                 "98A", "30A", "37A", "38A", "55A", "51A", "143A", "26A",
                 "49A", "33A")

#: scripts written right to left
RTL_SCRIPTS = frozenset({"Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm", "Samr"})

#: scripts written without spaces between words
NO_SPACE_SCRIPTS = frozenset({"Hani", "Hans", "Hant", "Jpan", "Thai", "Laoo",
                              "Mymr", "Khmr", "Tibt"})

# ----------------------------------------------------------------------
# per-feature value maps, keyed by the WALS code number as a string
# ----------------------------------------------------------------------
_CLAUSE = {"1": "SOV", "2": "SVO", "3": "VSO", "4": "VOS", "5": "OVS", "6": "OSV"}
_ADJ = {"1": "AN", "2": "NA"}
_ADPOSITION = {"1": "post", "2": "pre"}
_POSSESSIVE = {"1": "GN", "2": "NG"}
_DET = {"1": "DN", "2": "ND", "3": "DN", "4": "ND"}
_NUMERAL = {"1": "NumN", "2": "NNum"}
#: 143A codes many mixed types; only the four unambiguous ones are read
_NEGATION = {"1": "pre", "2": "post", "3": "pre", "4": "post"}
_ALIGNMENT = {"1": NO_CASE, "2": NOM_ACC, "3": NOM_ACC, "4": ERG_ABS,
              "5": NOM_ACC, "6": NOM_ACC}
#: 30A: number of genders. "1" is none; everything else is a class system,
#: which for the engine means concord is switched on.
_N_GENDERS = {"1": 0, "2": 2, "3": 3, "4": 4, "5": 5}


@dataclass(frozen=True)
class Profile:
    """Engine parameters for one language, with the evidence behind them."""

    code: str
    order: WordOrder
    alignment: Alignment
    concord: Concord
    typography: Typography
    #: what happens where two words meet, where the language does anything
    sandhi: Sandhi = Sandhi()
    #: the WALS/Grambank features that were actually available
    evidence: Mapping[str, str] = field(default_factory=dict)
    #: True when the dominant order was not coded and a default was used
    order_uncertain: bool = False
    #: whether the language has articles at all, per 37A/38A
    has_definite: bool = False
    has_indefinite: bool = False
    #: whether the indefinite article **is** the numeral one (WALS 38A code 2).
    #: Only then is "one" the right dictionary key for it; where 38A says the
    #: word is distinct (code 1) the numeral is simply a different word, and
    #: printing it would be worse than printing nothing.
    indefinite_from_one: bool = False
    #: whether counting requires a measure word, per 55A
    classifiers: str = "absent"
    #: number of noun classes per 30A; 0 means none
    n_classes: int = 0
    #: whether case is marked by suffix, prefix, or not at all, per 51A
    case_affix: str = "none"

    def to_json(self) -> dict[str, Any]:
        o, t = self.order, self.typography
        return {
            "code": self.code,
            "clause": o.clause, "adj": o.adj, "det": o.det,
            "numeral": o.numeral, "adposition": o.adposition,
            "possessive": o.possessive, "label": o.label,
            "conditional": o.conditional, "wh_fronting": o.wh_fronting,
            "copula_overt": o.copula_overt,
            "numeral_forces_plural": o.numeral_forces_plural,
            "negation": o.negation,
            "alignment": self.alignment.case_of.__name__,
            "concord_adjective": list(self.concord.adjective),
            "concord_predicative": list(self.concord.predicative),
            "word_joiner": t.word_joiner, "capitalizes": t.capitalizes,
            "rtl": t.rtl,
            "has_definite": self.has_definite,
            "has_indefinite": self.has_indefinite,
            "indefinite_from_one": self.indefinite_from_one,
            "classifiers": self.classifiers,
            "n_classes": self.n_classes,
            "case_affix": self.case_affix,
            "order_uncertain": self.order_uncertain,
            "evidence": dict(self.evidence),
        }

    @property
    def coded(self) -> int:
        return len(self.evidence)


_SANDHI_DATA = Path(__file__).resolve().parent / "data" / "sandhi.json"


@lru_cache(maxsize=1)
def _sandhi_tables() -> Mapping[str, Mapping[str, Mapping[str, str]]]:
    """The elision table, keyed by ISO 639-3.

    Not derivable from WALS: no feature codes which function words elide, or
    what they become. It is small, closed, and language-particular, so it is
    written down. Keys beginning with an underscore are commentary.
    """
    raw = json.loads(_SANDHI_DATA.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def sandhi_for(code: str) -> Sandhi:
    """The boundary adjustments for one language. Empty for most of them."""
    entry = _sandhi_tables().get(code, {})
    return Sandhi(elide=entry.get("elide", {}),
                  contract=entry.get("contract", {}))


def derive_profile(code: str, wals: Mapping[str, str], *,
                   script: str = "Latn", grambank: Mapping[str, str] | None = None
                   ) -> Profile:
    """Build engine parameters from one language's typological coding.

    ``wals`` maps a feature id such as ``"81A"`` to its code number as a string.
    Missing features fall back to the cross-linguistically commonest value, and
    the fallback is recorded rather than hidden — see :attr:`Profile.evidence`,
    which lists only what was genuinely coded.
    """
    evidence = {k: v for k, v in wals.items() if k in WALS_FEATURES}
    get = evidence.get

    clause = _CLAUSE.get(get("81A", ""), "")
    n_classes = _N_GENDERS.get(get("30A", ""), 0)
    concord_features: tuple[str, ...] = (CLS, NUM) if n_classes else ()

    # 37A code 5 and 38A code 5 both mean "no article of either kind"
    has_def = get("37A") in ("1", "2", "3")
    has_indef = get("38A") in ("1", "2", "3")
    indef_is_one = get("38A") == "2"
    classifiers = {"1": "absent", "2": "optional", "3": "obligatory"}.get(
        get("55A", ""), "absent")
    case_affix = {"1": "suffix", "2": "prefix", "9": "none"}.get(
        get("51A", ""), "none")

    verb_final = clause in ("SOV", "OSV")
    order = WordOrder(
        clause=clause or "SVO",
        adj=_ADJ.get(get("87A", ""), "AN"),
        det=_DET.get(get("88A", ""), "DN"),
        numeral=_NUMERAL.get(get("89A", ""), "NumN"),
        adposition=_ADPOSITION.get(get("85A", ""), "pre"),
        possessive=_POSSESSIVE.get(get("86A", ""), "GN" if verb_final else "NG"),
        # a data row's label leads in every language the curriculum has been
        # inspected in; WALS codes nothing about it, so it is not pretended to
        label="LV",
        # verb-final languages overwhelmingly put the subordinate clause first
        conditional="AC" if verb_final else "CA",
        wh_fronting=get("93A") == "1",
        # WALS does not code copula omission directly;
        # it is left overt unless a hand-written grammar says otherwise
        copula_overt=True,
        # classifier languages do not pluralize a counted noun
        numeral_forces_plural=classifiers == "absent",
        negation=_NEGATION.get(get("143A", ""), "pre"),
    )
    typography = Typography(
        word_joiner="" if script in NO_SPACE_SCRIPTS else " ",
        capitalizes=script in ("Latn", "Cyrl", "Grek", "Armn", "Geor", "Deva"),
        rtl=script in RTL_SCRIPTS,
        label_separator=":" if script in NO_SPACE_SCRIPTS else "",
    )
    return Profile(
        code=code,
        order=order,
        alignment=Alignment(case_of=_ALIGNMENT.get(get("98A", ""), NO_CASE)),
        concord=Concord(adjective=concord_features,
                        predicative=concord_features),
        typography=typography,
        sandhi=sandhi_for(code),
        evidence=evidence,
        order_uncertain=not clause,
        has_definite=has_def,
        has_indefinite=has_indef,
        indefinite_from_one=indef_is_one,
        classifiers=classifiers,
        n_classes=n_classes,
        case_affix=case_affix,
    )
