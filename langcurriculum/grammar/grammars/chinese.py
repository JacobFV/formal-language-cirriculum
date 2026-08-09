"""Mandarin: measure words, 的 modification, 吗 questions, no spacing.

Chinese is the grammar that proves the engine is not English with substituted
words, and it is also the one that most needed the parameterization to be about
*absence* as well as presence. Almost everything it does is something a
Eurocentric design would have to special-case:

* **No inflection at all.** No plural, no agreement, no tense. The morphology is
  :class:`~langcurriculum.grammar.morphology.IsolatingMorphology`, which is the
  identity — and being able to say "this language does not do that" in the same
  vocabulary as everything else is why the linearizer has no branches for it.
* **Measure words.** Counting or pointing goes through a classifier, per noun:
  三本书, 这个立方体, 一把铲子. ``个`` is the deliberate fallback, because an
  over-general 个 is acceptable and a wrong specific classifier is not.
* **的 for modification, per adjective.** 红色的立方体 links; 大立方体 does not.
  The vocabulary records which, so this is data rather than a guess.
* **Topic–comment framing.** A field becomes a topic and its comment, not a
  copular sentence, because 是 would have to know whether the comment is nominal
  and for an arbitrary field that is not knowable.
* **No spaces, full-width punctuation, no capitalization.** All three fall out of
  :class:`~langcurriculum.grammar.linearize.Typography`.

Not attempted
-------------

No 把 or 被 constructions, no resultative complements, no 是…的 cleft — these
need argument structure the curriculum's flat predicates do not carry. No
numeral-to-character conversion: digits stay digits, which is standard in
written technical Chinese and avoids guessing at 二 versus 两.
"""

from __future__ import annotations

from typing import Any

from ..category import A, CLF, N, NUM
from ..features import EMPTY, FS
from ..linearize import (
    NO_CASE, Alignment, Concord, Typography, WordOrder,
)
from ..morphology import IsolatingMorphology
from ..syntax import Node
from .vocab import VocabularyGrammar

__all__ = ["Chinese", "DEFAULT_CLASSIFIER"]

#: the general-purpose measure word, used where the vocabulary has no opinion
DEFAULT_CLASSIFIER = "个"

_CLOSED = {
    "the": "这", "a": "一", "not": "不", "and": "和", "or": "或", "of": "的",
    "if": "若", "then": "则", "to": "给", "at": "在", "empty": "空",
    "what": "什么", "which": "哪个", "who": "谁", "where": "哪里",
    "when": "什么时候", "why": "为什么", "how": "怎么", "how_many": "多少",
    "all": "所有", "some": "有", "none": "没有", "most": "大多数",
    "few": "少数", "exactly_two": "恰好两个",
    "q_particle": "吗", "high": "高", "low": "低",
    "gt": "大于", "lt": "小于", "ge": "至少是", "le": "至多是",
    "eq": "等于", "neq": "不等于",
    "step": "第", "round": "第", "trial": "第", "turn": "第",
    "case": "例", "block": "块", "stage": "阶段",
    "is": "是", "are": "是",
}

_RELATIONS = {
    "imp": "蕴含", "implies": "蕴含", "iff": "当且仅当",
    "entails": "蕴含", "supports": "支持", "attacks": "攻击",
    "contradicts": "与之矛盾", "isa": "是一种", "is_a": "是一种",
    "requires": "需要", "provides": "提供", "feeds": "供给",
    "causes": "导致", "precedes": "先于", "after": "在之后",
    "means": "的意思是", "says": "说", "claims": "声称",
    "has": "有", "holds": "对其成立",
    "add": "加", "sub": "减", "mul": "乘以", "div": "除以",
    "mod": "模", "pow": "的次方是",
    "left_of": "的左边", "right_of": "的右边", "above": "的上方",
    "below": "的下方", "near": "的附近", "inside": "的里面",
    "front_of": "的前面", "behind": "的后面", "on": "的上面",
}


class Chinese(VocabularyGrammar):
    """Mandarin prose, simplified characters, on the grammar engine."""

    code = "chinese"
    name = "Chinese (Mandarin, Simplified)"
    pack = "chinese"
    iso = "cmn"

    order = WordOrder(
        clause="SVO", adj="AN", det="DN", numeral="NumN",
        adposition="pre", possessive="GN", label="LV", conditional="AC",
        wh_fronting=False,           # in situ: 哪个物体是红色的？
        copula_overt=True,           # 是, for identity
        numeral_forces_plural=False,  # the measure word does that work
        negation="pre",
    )
    typography = Typography(
        word_joiner="", capitalizes=False,
        full_stop="。", question_mark="？",
        list_separator="，", item_separator="、", clause_separator="；",
        colon="：", label_separator="：", bullet="  - ",
        arg_separator=", ",          # a Latin call stays half-width
    )
    alignment = Alignment(case_of=NO_CASE)
    #: nothing agrees with anything: Chinese has no inflection to agree with
    concord = Concord()

    notes = (
        "no inflection: no plural, no agreement, no verb tense",
        "measure words for counting and pointing (三本书, 这个立方体)",
        "的 for adjectival modification, recorded per adjective",
        "topic–comment framing of each section",
        "questions by particle (吗) and in-situ wh-words, never by inversion",
        "the enumerating comma 、 for items but ； between clauses",
        "no spaces, full-width punctuation, no capitalization",
        "NOT attempted: 把/被 constructions, resultative complements, the "
        "是…的 cleft, numeral-to-character conversion",
    )

    def __init__(self) -> None:
        super().__init__()
        self.closed = {**_CLOSED, **self.closed}
        self.predicate_words = {**_RELATIONS, **self.predicate_words}
        self.paradigms = {
            "pronouns": {"f": "她", "m": "他"},
            "name_gender": {"alice": "f", "bob": "m", "carol": "f",
                            "dave": "m", "erin": "f", "frank": "m"},
        }
        self.morphology[N.name] = IsolatingMorphology()
        self.morphology[A.name] = IsolatingMorphology()

    # ---- classifiers ------------------------------------------------------
    def classifier(self, lemma: str) -> str:
        noun = self.vocabulary.nouns.get(lemma)
        return (noun.classifier if noun and noun.classifier else DEFAULT_CLASSIFIER)

    def determiner(self, kind: str, head: Node | None, feats: FS) -> str:
        """A determiner never stands alone: it combines with a measure word.

        这 and 一 are not articles and cannot modify a noun by themselves —
        *这书 is not Chinese. Both go through the classifier, which is why this
        returns the pair rather than the determiner.
        """
        if kind not in ("def", "indef") or head is None:
            return ""
        word = self.cw("the") if kind == "def" else self.cw("a")
        return f"{word}{self.classifier(head.lemma)}"

    def numeral_phrase(self, count: str, head: Node | None, feats: FS) -> str:
        """``3本`` — the numeral and the measure word are one constituent."""
        if head is None:
            return count
        return f"{count}{self.classifier(head.lemma)}"

    # ---- 的 modification --------------------------------------------------
    def inflect(self, cat: str, lemma: str, feats: FS) -> str:
        """An attributive adjective links with 的 where the vocabulary says so."""
        surface = self.word(lemma, pos=cat)
        if cat != A.name:
            return surface
        adjective = self.vocabulary.adjectives.get(lemma)
        if adjective is None:
            return surface
        return adjective.base + ("的" if adjective.linker else "")

    def attribute(self, lemma: str) -> str:
        """An adjective used predicatively always takes 的: 红色的, 大的."""
        adjective = self.vocabulary.adjectives.get(lemma)
        return (adjective.base + "的") if adjective else self.word(lemma)

    # ---- coordination -----------------------------------------------------
    def join_list(self, items):
        """``甲、乙和丙`` — the enumerating comma, then 和 before the last."""
        items = [i for i in items if i]
        if len(items) <= 1:
            return items[0] if items else ""
        return "、".join(items[:-1]) + self.cw("and") + items[-1]

    def join_clauses(self, items):
        """Clauses take ；, never 、.

        Running whole clauses together with the enumerating comma is the single
        most common way translated Chinese gives itself away.
        """
        return self.typography.clause_separator.join(i for i in items if i)

    # ---- topic–comment ----------------------------------------------------
    def lin_PredAttr(self, node: Node, ctx: FS) -> str:
        """``o0是红色的`` — a predicative adjective keeps its 的."""
        subject, attribute = node.arg("agent"), node.arg("attribute")
        assert subject is not None and attribute is not None
        head = self._head_lemma(attribute)
        realized = self.attribute(head.lemma) if head is not None \
            else self.lin(attribute, ctx)
        return f"{self.lin(subject, ctx)}是{realized}"

    def lin_Labelled(self, node: Node, ctx: FS) -> str:
        """A single value under a label is a data row, not a sentence.

        Chinese orders 类型X and X不可靠 differently, and which one a bare unary
        predicate wants is not knowable from the structure. The labelled row is
        right either way.
        """
        label, value = node.arg("label"), node.arg("value")
        assert label is not None and value is not None
        return (f"{self.clean_label(self.lin(label, ctx))}"
                f"{self.typography.colon}{self.lin(value, ctx)}")

    def clean_label(self, label: str) -> str:
        """Drop a leading 的 and a trailing 是: both need what is not there."""
        return label.lstrip("的").rstrip("是") or label

    def block_heading(self, name: str) -> str:
        return f"{name.replace('_', ' ')}{self.typography.colon}"

    # ---- questions --------------------------------------------------------
    def lin_YNQ(self, node: Node, ctx: FS) -> str:
        """``…吗`` — a particle, never inversion."""
        body = node.arg("body")
        assert body is not None
        return f"{self.lin(body, ctx)}{self.cw('q_particle')}"

    def lin_AltQ(self, node: Node, ctx: FS) -> str:
        """``甲是高还是低？`` — an alternative question takes 还是, never 或.

        ``或`` coordinates alternatives in a *statement*; using it in a question
        is one of the tells of translated Chinese, and the two are not
        interchangeable.
        """
        body = node.arg("body")
        options = [self.lin(o, ctx) for o in node.all_args("option")]
        inner = self.lin(body, ctx) if body is not None else ""
        return f"{inner}是{'还是'.join(options)}" if options else inner

    def sentence(self, text: str, end: str | None = None) -> str:
        text = text.strip()
        if not text:
            return ""
        if end == "":
            return text
        end = self.typography.full_stop if end is None else end
        return text if text[-1] in "。？！.?!" else text + end
