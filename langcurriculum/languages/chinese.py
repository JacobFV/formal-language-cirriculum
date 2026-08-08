"""The Chinese pack: classifiers, 的 modification, 吗 questions, no spacing.

Chinese is the pack that proves the realizer is not English with substituted
words. Almost every strategy is overridden, and the ones that are not are the
ones that genuinely do not vary.

What this pack implements
-------------------------

* **No inflection at all.** No plural, no agreement, no tense on the verb. The
  vocabulary carries a single form, and an aspect particle (``了``) only where
  the source is unambiguously past.
* **Measure words.** Every noun carries its classifier, and counting or pointing
  goes through it: ``三本书``, ``这个立方体``, ``一把铲子``. ``个`` is the default
  where the vocabulary is unsure, because an over-general ``个`` is acceptable
  and a wrong specific classifier is not.
* **的 for modification.** Disyllabic and colour adjectives link with ``的``
  (``红色的立方体``); monosyllabic ones attach directly (``大立方体``). The
  vocabulary records which, per adjective.
* **Topic–comment framing.** A field becomes a topic followed by its comment —
  ``场景中：…`` — rather than an English "The scene is …" copular sentence.
* **Question particles, not inversion.** A yes/no question ends in ``吗？``; a
  content question uses ``什么 / 哪个 / 多少 / 谁`` in situ. Nothing is fronted,
  because Chinese does not front.
* **No spaces, full-width punctuation.** ``word_joiner`` is empty, so the shared
  walk concatenates; ``，。：？`` throughout; no capitalization, because there is
  no case.

What it deliberately does not attempt
-------------------------------------

* **No 把 or 被 constructions, no resultative complements, no 是…的 cleft.**
  These need argument structure the curriculum's flat predicates do not carry.
* **No numeral-to-character conversion.** Digits stay as digits (``3个``), which
  is standard in written technical Chinese and avoids guessing at 二/两.
* **Predicate heads the vocabulary does not translate** become a labelled row
  carrying the source identifier, not a guessed Chinese verb.
"""

from __future__ import annotations

from .base import Lexicon, NaturalLanguage
from .lexicon import load_vocabulary

__all__ = ["CHINESE", "Chinese"]

_VOCAB, _RAW = load_vocabulary("chinese")

#: the general-purpose measure word, used when the vocabulary has no opinion
DEFAULT_CLASSIFIER = "个"

_OPERATORS = {
    "and": "并且", "or": "或者", "imp": "蕴含", "implies": "蕴含",
    "iff": "当且仅当", "eq": "等于", "neq": "不等于",
    "entails": "蕴含", "supports": "支持", "attacks": "攻击",
    "contradicts": "与之矛盾", "isa": "是一种", "is_a": "是一种",
    "add": "加", "sub": "减", "mul": "乘以", "div": "除以",
    "mod": "模", "pow": "的次方是", "lt": "小于", "gt": "大于",
    "le": "至多是", "ge": "至少是",
    "requires": "需要", "provides": "提供", "feeds": "供给",
    "causes": "导致", "precedes": "先于", "after": "在之后",
}

_PREPOSITIONS = {
    "left_of": "在左边", "right_of": "在右边", "above": "在上方",
    "below": "在下方", "near": "在附近", "inside": "在里面",
    "front_of": "在前面", "behind": "在后面", "on": "在上面", "at": "在",
}

#: the forms the quantifier questions actually use, so that the dictionary
#: entry and the sentence agree
_QUANTIFIERS = {"all": "所有", "some": "有", "none": "没有",
                "exactly_two": "恰好两个", "most": "大多数", "few": "少数"}

_PREFIX_OPERATORS = {"not": "并非", "neg": "并非", "no": "没有"}


# --------------------------------------------------------------------------
# templates needing the source words (classifier and 的 selection)
# --------------------------------------------------------------------------
def _obj5(lang, terms):
    """``(obj o0 red cube 4 8)`` -> ``o0是一个红色的立方体，位于(4, 8)``."""
    oid, color, shape, x, y = (t.value for t in terms[:5])
    np = lang.noun_phrase(str(shape), adjectives=[str(color)], determiner="indef")
    return f"{lang.text(oid)}是{np}，位于({x},{y})"


def _obj3(lang, terms):
    oid, color, shape = (t.value for t in terms[:3])
    return f"{lang.text(oid)}是{lang.noun_phrase(str(shape), adjectives=[str(color)], determiner='indef')}"


def _obj4(lang, terms):
    oid, color, x, y = (t.value for t in terms[:4])
    return f"{lang.text(oid)}是{lang.attribute(str(color))}，位于({x},{y})"


def _color2(lang, terms):
    oid, color = (t.value for t in terms[:2])
    return f"{lang.text(oid)}是{lang.attribute(str(color))}"


def _shape2(lang, terms):
    oid, shape = (t.value for t in terms[:2])
    return f"{lang.text(oid)}是{lang.noun_phrase(str(shape), determiner='indef')}"


def _fact2(lang, terms):
    kind, who = (t.value for t in terms[:2])
    return f"{lang.text(who)}是{lang.noun_phrase(str(kind), determiner='indef')}"


def _isa2(lang, terms):
    a, b = (t.value for t in terms[:2])
    return f"{lang.text(a)}是一种{lang.word(str(b))}"


def _spatial(word):
    def _rel(lang, terms):
        color, shape = (t.value for t in terms[:2])
        return f"在{lang.noun_phrase(str(shape), adjectives=[str(color)])}{word}"
    return _rel


_PREDICATE_TEMPLATES = {
    "obj/5": _obj5, "obj/4": _obj4, "obj/3": _obj3,
    "color/2": _color2, "shape/2": _shape2,
    "fact/2": _fact2, "isa/2": _isa2, "inst/2": _isa2, "entity/2": _isa2,
    "left_of/2": _spatial("的左边"), "right_of/2": _spatial("的右边"),
    "above/2": _spatial("的上方"), "below/2": _spatial("的下方"),
    "ex/2": "{0} → {1}",
    "rule/2": "{0}蕴含{1}",
    "rule/3": "规则{0}：若{2}则{1}",
    "means/2": "{0}的意思是{1}",
    "says/2": "{0}说{1}",
    "claims/2": "{0}声称{1}",
    "bind/2": "{0}绑定到{1}",
    "at/1": "位置{0}",
    "leaf/1": "叶子{0}",
    "step/4": "第{0}步：{1}{2}{3}",
    "step/3": "第{0}步：{1}{2}",
    "observed/2": "观察到{0}是{1}",
    "predicts/3": "{0}对{1}的预测是{2}",
    "predicts/2": "{0}预测{1}",
    "vote/3": "第{0}轮，{1}投了{2}",
    "cost/2": "{0}的成本是{1}",
    "bits/2": "{0}占{1}比特",
    "value/2": "{0}的值是{1}",
    "set/2": "{0}设为{1}",
    "has/2": "{0}有{1}",
    "prop/2": "{0}是{1}",
    "type/1": "类型{0}",
    "candidate/2": "{0}：{1}",
    "candidate/1": "{0}",
    "claim/1": "{0}",
    "claim/3": "{0}：{1}导致{2}",
    "macro/2": "{0}是{1}的简写",
    "coalition/2": "联盟{0}的价值是{1}",
    "event/3": "{0}从{1}持续到{2}",
    "give/3": "{0}把{2}给了{1}",
    "word/2": "{0}出现了{1}次",
    "formula/2": "{0}：{1}",
    "theory/2": "{0}：{1}",
    "quant/2": "其中{0}是{1}",
    "parent/2": "{0}是{1}的家长",
    "adjudicated/4": "第{0}次试验：{1}在{2}上是{3}",
    "obs/3": "在第{0}块中，{1}={2}",
    "do/3": "在第{0}块中，把{1}设为{2}",
    "after/4": "第{0}块第{1}次运行：{2}={3}",
    "item/4": "{0}：{1}，{2}，{3}",
    "input/3": "第{0}例第{1}位：{2}",
    "output/3": "第{0}例第{1}位：{2}",
    "turn/3": "第{0}轮：{1}{2}",
    "dim/4": "{0}的量纲是({1},{2},{3})",
    "needs/3": "{0}需要{1}={2}",
    "norm/5": "{0}（优先级{1}）：若{2}，则{4}为{3}",
    "kb_rule/3": "{0}记录：{1}蕴含{2}",
    "kb_fact/3": "{0}记录：{1}是{2}",
    "apply/2": "apply({0}, {1})",
    "at_start/1": "开始时的{0}",
    "at_end/1": "结束时的{0}",
    "color/1": "颜色为{0}",
    "shape/1": "形状为{0}",
    "resolve_by/1": "按{0}裁决",
    "schema/2": "{0}：{1}",
    "equation/2": "{0}：{1}",
}


def _quant(lang, terms):
    """One construction per quantifier. 有些…都 is a contradiction, so it is avoided."""
    q, what = (t.value for t in terms[:2])
    attr = lang.attribute(str(what))
    return {
        "all": f"所有物体都是{attr}吗？",
        "some": f"有物体是{attr}吗？",
        "none": f"是否没有物体是{attr}？",
        "exactly_two": f"恰好两个物体是{attr}吗？",
    }.get(str(q), f"有物体是{attr}吗？")


def _q_which(lang, terms):
    color, shape = (t.value for t in terms[:2])
    return f"哪个物体是{lang.noun_phrase(str(shape), adjectives=[str(color)])}？"


def _q_the(lang, terms):
    color = terms[0].value
    rest = lang.clause(terms[1]) if len(terms) > 1 else ""
    return f"请找出{rest}{lang.attribute(str(color))}物体。"


_QUERY_TEMPLATES = {
    "which": _q_which,
    "the": _q_the,
    "which_color": "{0}表示什么颜色？",
    "classify": "{0}是高还是低？",
    "at": "位置{0}上的符号是什么？",
    "accept": "字符串{0}属于该语言吗？",
    "balanced": "该字符串是否配对平衡？",
    "palindrome": "该字符串是回文吗？",
    "max_depth": "该字符串的最大嵌套深度是多少？",
    "first_leaf": "这棵树的第一个叶子是什么？",
    "next": "接下来是什么？",
    "quant": _quant,
    "find": "请找出{0}对应的物体。",
    "value_of": "{0}绑定到什么？",
    "unify": "{0}与什么合一？",
    "holds": "{0}对{1}成立吗？",
    "answer": "答案是什么？",
    "who": "谁{0}？",
    "how_many": "有多少个{0}？",
    "resolve_query_in": "请回答{0}一半中的问题。",
}

CHINESE = Lexicon(
    definite="这", indefinite="一",
    copula_sg="是", copula_pl="是",
    negation="不", conjunction="和", disjunction="或", yes="是", no="否", of="的",
    word_joiner="", capitalizes=False,
    full_stop="。", question_mark="？", question_open="",
    list_separator="，", clause_separator="；", colon="：", bullet="  - ",
    arg_separator=", ",
    operators=_OPERATORS, prepositions=_PREPOSITIONS, quantifiers=_QUANTIFIERS,
    prefix_operators=_PREFIX_OPERATORS,
    field_intros=dict(_RAW.get("field_intros") or {}),
    predicate_words=dict(_RAW.get("predicate_words") or {}),
    predicate_templates={**{k: v for k, v in (_RAW.get("predicate_templates") or {}).items()},
                         **_PREDICATE_TEMPLATES},
    query_templates={**{k: v for k, v in (_RAW.get("query_templates") or {}).items()},
                     **_QUERY_TEMPLATES},
    instruction="请从以下选项中选出恰好一个作答：{choices}\n只回答答案本身。",
    instruction_many="请从上面列出的{n}个选项中选出恰好一个作答。\n只回答答案本身。",
    options_heading="选项：",
    pronouns={"f": "她", "m": "他"},
    name_gender={"alice": "f", "bob": "m", "carol": "f",
                 "dave": "m", "erin": "f", "frank": "m"},
    vocabulary=_VOCAB,
)


class Chinese(NaturalLanguage):
    """Mandarin Chinese prose, simplified characters."""

    grammar_notes = (
        "no inflection: no plural, no agreement, no verb tense",
        "measure words for counting and pointing (三本书, 这个立方体)",
        "的 for adjectival modification, per-adjective",
        "topic–comment framing of each section",
        "questions by particle (吗) and in-situ wh-words, never by inversion",
        "no spaces; full-width punctuation",
    )

    def __init__(self):
        super().__init__(
            code="chinese", name="Chinese (Mandarin, Simplified)", lexicon=CHINESE,
            description="Mandarin prose with measure words, 的 modification and 吗 questions.")

    # ---- morphology: there is none -------------------------------------
    def pluralize(self, word: str) -> str:
        """Chinese does not inflect for number. The measure word does that work."""
        return word

    def classifier(self, noun_key: str) -> str:
        noun = self.lexicon.vocabulary.nouns.get(noun_key)
        return (noun.classifier if noun and noun.classifier else DEFAULT_CLASSIFIER)

    def attribute(self, key: str) -> str:
        """An adjective used predicatively: ``红色的``, ``大的``."""
        adj = self.lexicon.vocabulary.adjectives.get(key)
        if adj is None:
            return self.word(key)
        return adj.base + "的"

    def adjective(self, key, *, gender="m", plural=False):
        """Attributively: ``红色的`` links with 的, ``大`` attaches directly."""
        adj = self.lexicon.vocabulary.adjectives.get(key)
        if adj is None:
            return self.word(key)
        return adj.base + ("的" if adj.linker else "")

    # ---- phrase building ------------------------------------------------
    def determiner(self, kind, *, gender="m", plural=False, word=""):
        # a bare determiner is never used on its own in Chinese: it always
        # combines with a measure word, which noun_phrase does
        return ""

    def noun_phrase(self, noun_key, *, adjectives=(), determiner=None,
                    count=None, plural=False):
        """``[numeral|这][classifier][adjective(的)]noun`` — and never a plural."""
        noun = self.lexicon.vocabulary.nouns.get(noun_key)
        head = noun.lemma if noun else self.word(noun_key)
        adjs = "".join(self.adjective(a) for a in adjectives)
        prefix = ""
        if count is not None:
            prefix = f"{count}{self.classifier(noun_key)}"
        elif determiner == "def":
            prefix = f"{self.lexicon.definite}{self.classifier(noun_key)}"
        elif determiner == "indef":
            prefix = f"{self.lexicon.indefinite}{self.classifier(noun_key)}"
        return f"{prefix}{adjs}{head}"

    # ---- syntax ---------------------------------------------------------
    def join_list(self, items):
        """``a、b和c`` — the enumerating comma, then 和 before the last."""
        items = [i for i in items if i]
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        return "、".join(items[:-1]) + self.lexicon.conjunction + items[-1]

    def join_clauses(self, items):
        """Clauses are separated by the full-width semicolon, not by 、.

        ``、`` enumerates items. Running whole clauses together with it is the
        single most common way translated Chinese gives itself away.
        """
        items = [i for i in items if i]
        return self.lexicon.clause_separator.join(items)

    def attributive(self, entity, attribute):
        """Topic–comment, not a copular sentence.

        ``是`` would need to know whether the comment is nominal, and for an
        arbitrary field it is not knowable, so the safe construction is the one
        Chinese uses for exactly this: state the topic, then the comment.
        """
        return f"{entity}{self.lexicon.colon}{attribute}"

    def clean_label(self, label):
        """Drop a leading 的 and a trailing 是 — they need a subject that is not there."""
        return label.lstrip("的").rstrip("是") or label

    def labelled(self, label, value):
        """A single value under a label is a data row, not a sentence.

        Chinese would order ``X不可靠`` and ``类型X`` differently, and which one a
        bare unary predicate wants is not knowable from the structure. The
        labelled row is right either way.
        """
        return f"{self.clean_label(label)}{self.lexicon.colon}{value}"

    def enumerated(self, label, values):
        return f"{self.clean_label(label)}{self.lexicon.colon}{self.join_list(values)}"

    def relational(self, subject, relation, obj):
        return f"{subject}{relation}{obj}"

    def bullet_heading(self, name):
        return f"{name.replace('_', ' ')}{self.lexicon.colon}"

    def field_sentence(self, name, body, *, is_list, intro):
        if intro:
            return self.sentence(f"{intro}{body}")
        return self.sentence(f"{name.replace('_', ' ')}{self.lexicon.colon}{body}")

    def generic_question(self, head, args):
        """No template: ask for the named value in situ, with 是什么.

        The head keeps its source identifier rather than acquiring an invented
        Chinese noun.
        """
        joined = "".join(a for a in args if a)
        words = self.lexicon.predicate_words.get(head)
        subject = self.clean_label(words) if words else f"「{head}」"
        return f"{joined}的{subject}是什么" if joined else f"{subject}是什么"

    def sentence(self, text, end=None):
        text = text.strip()
        if not text:
            return ""
        if end == "":
            return text
        end = self.lexicon.full_stop if end is None else end
        return text if text[-1] in "。？！.?!" else text + end
