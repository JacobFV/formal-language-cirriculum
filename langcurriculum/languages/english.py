"""The English pack: the words, and the two variants built from them.

This is one entry in the language registry, not a special case in the code. Every
English-specific decision lives in :data:`ENGLISH` below — the closed-class
inventory, the operator and preposition words, the templates that make a common
structure read naturally, and the inflected material the agreement lessons need.
The realizer that arranges them is in :mod:`langcurriculum.languages.base` and
knows nothing about English.

Two variants ship:

``english``
    the default. Prose.

``english_synonym``
    the same prose with the **question's** content words swapped for near
    synonyms the learner has not met — ``red`` becomes ``crimson``, ``cube``
    becomes ``block`` — while the body of the episode keeps the original words.
    The asymmetry is the test: the learner has to connect a word it has never
    seen to one it has, and a model that memorized the training vocabulary
    rather than its meaning loses accuracy here. Substituting in both places
    would make the episode *easier* than the default, not harder.
"""

from __future__ import annotations

import re

from .base import Lexicon, NaturalLanguage
from .lexicon import load_vocabulary

_ENDS_SENTENCE = re.compile(r"[.!?]$").search
#: "a orange cube" -> "an orange cube"; English article agreement is phonological,
#: so it is fixed after the words are chosen rather than at every template.
_A_BEFORE_VOWEL = re.compile(r"\ba (?=[aeiou])")

__all__ = ["ENGLISH", "SYNONYMS", "SHAPE_SYNONYMS", "English", "EnglishSynonym"]

#: colour synonyms, held out of the default vocabulary
SYNONYMS = {"red": "crimson", "blue": "azure", "green": "emerald",
            "yellow": "golden", "purple": "violet", "orange": "amber"}
#: shape synonyms, likewise
SHAPE_SYNONYMS = {"cube": "block", "sphere": "ball", "cone": "funnel",
                  "prism": "wedge", "disc": "plate", "rod": "stick"}

# --------------------------------------------------------------------------
# operator and relation words
# --------------------------------------------------------------------------
_OPERATORS = {
    # logical
    "and": "and", "or": "or", "imp": "implies", "implies": "implies",
    "iff": "if and only if", "eq": "equals", "neq": "does not equal",
    "entails": "entails", "supports": "supports", "attacks": "attacks",
    "contradicts": "contradicts", "isa": "is a", "is_a": "is a",
    # arithmetic
    "add": "plus", "sub": "minus", "mul": "times", "div": "divided by",
    "mod": "modulo", "pow": "to the power", "lt": "is less than",
    "gt": "is greater than", "le": "is at most", "ge": "is at least",
    # dependency
    "requires": "requires", "provides": "provides", "feeds": "feeds",
    "causes": "causes", "precedes": "comes before", "after": "after",
}

_PREPOSITIONS = {
    "left_of": "to the left of", "right_of": "to the right of",
    "above": "above", "below": "below", "near": "next to", "inside": "inside",
    "front_of": "in front of", "behind": "behind", "on": "on", "at": "at",
}

_QUANTIFIERS = {"all": "all", "some": "some", "none": "none",
                "exactly_two": "exactly two", "most": "most", "few": "few"}

_PREFIX_OPERATORS = {"not": "not", "neg": "not", "no": "no"}

# --------------------------------------------------------------------------
# how each part of an episode is introduced
# --------------------------------------------------------------------------
_FIELD_INTROS = {
    "scene": "In the scene:",
    "world": "The world contains:",
    "lexicon": "You are told:",
    "examples": "You are shown these examples:",
    "demonstrations": "You are shown these demonstrations:",
    "facts": "You know these facts:",
    "premises": "The premises are:",
    "axioms": "The axioms are:",
    "rules": "The rules are:",
    "rule": "The rule is",
    "candidates": "The candidates are:",
    "options": "The options are:",
    "claims": "The claims are:",
    "reports": "The reports are:",
    "hypotheses": "The hypotheses are:",
    "theories": "The theories are:",
    "data": "The data are:",
    "observations": "The observations are:",
    "history": "What happened before:",
    "trajectory": "The trajectory so far:",
    "log": "The log reads:",
    "transcript": "The transcript reads:",
    "discourse": "The discourse so far:",
    "dialogue": "The dialogue so far:",
    "said": "What was said:",
    "sentence": "The sentence is",
    "string": "The string is",
    "sequence": "The sequence is",
    "symbols": "The symbols are",
    "program": "The program is:",
    "trace": "The trace is:",
    "instruction": "The instruction is",
    "goal": "The goal is",
    "goals": "The goals are:",
    "tasks": "The tasks are:",
    "state": "The current state is",
    "agent": "The agent is",
    "agents": "The agents are:",
    "entities": "The entities are:",
    "taxonomy": "The taxonomy says:",
    "semantics": "The semantics are:",
    "cost_model": "Costs:",
    "budget": "The budget is",
    "prerequisites": "The prerequisites are:",
    "variables": "The variables are:",
    "answer_options": "The legal answers are:",
    "tree": "The tree is",
    "substitution": "The substitution is:",
    "pattern": "The pattern is",
    "fact": "The fact is",
}

# --------------------------------------------------------------------------
# per-structure templates, keyed by head or by "head/arity"
# --------------------------------------------------------------------------
_PREDICATE_TEMPLATES = {
    "obj/5": "{0} is a {1} {2} at ({3}, {4})",
    "obj/3": "{0} is a {1} {2}",
    "round_obj/4": "in round {0}, {1} is a {2} {3}",
    "color/2": "{0} is {1}",
    "shape/2": "{0} is a {1}",
    "ex/2": "{0} → {1}",
    "example/2": "{0} → {1}",
    "rule/2": "{0} implies {1}",
    "rule/3": "rule {0}: {1} if {2}",
    "rule/4": "rule {0}: {1} if {2} ({3})",
    "means/2": "{0} means {1}",
    "says/2": "{0} says {1}",
    "claims/2": "{0} claims that {1}",
    "bind/2": "{0} is bound to {1}",
    "value_of/1": "the value of {0}",
    "leaf/1": "leaf {0}",
    "node/2": "a node over {0} and {1}",
    "at/1": "position {0}",
    "step/4": "step {0}: {1} {2} {3}",
    "step/3": "step {0}: {1} {2}",
    "observed/2": "{0} was observed to be {1}",
    "predicts/3": "{0} predicts {2} for {1}",
    "predicts/2": "{0} predicts {1}",
    "vote/3": "in round {0}, {1} voted {2}",
    "cost/2": "{0} costs {1}",
    "bits/2": "{0} takes {1} bits",
    "value/2": "{0} has value {1}",
    "set/2": "{0} is set to {1}",
    "weight/1": "weight {0}",
    "holds/2": "{0} holds of {1}",
    "has/2": "{0} has {1}",
    "prop/2": "{0} is {1}",
    "inst/2": "{0} is an instance of {1}",
    "type/1": "type {0}",
    "kb_fact/3": "{0} records that {1} is {2}",
    "candidate/2": "{0}: {1}",
    "macro/2": "{0} abbreviates {1}",
    "coalition/2": "the coalition {0} is worth {1}",
    "event/3": "{0} runs from {1} to {2}",
    "give/3": "{0} gives {2} to {1}",
    "trial/4": "trial {0}: {1} {2} {3}",
    "question/3": "{0} asks {1} {2}",
    "word/2": "{0} occurs {1} times",
    "reading/2": "reading {0}: {1}",
    "formula/2": "{0}: {1}",
    "theory/2": "{0}: {1}",
    "scores/3": "{0} scores {2} on {1}",
    "quant/2": "{0} of them are {1}",
    "parent/2": "{0} is a parent of {1}",
    # relations used as modifiers inside a referring expression
    "left_of/2": "to the left of the {0} {1}",
    "right_of/2": "to the right of the {0} {1}",
    "above/2": "above the {0} {1}",
    "below/2": "below the {0} {1}",
    "fact/2": "{1} is a {0}",
    "entity/2": "{0} is a {1}",
    "claim/1": "{0}",
    "claim/3": "{0}: {1} causes {2}",
    "do/3": "in block {0}, set {1} to {2}",
    "after/4": "block {0}, run {1}: {2} = {3}",
    "argument/1": "{0}",
    "candidate/1": "{0}",
    "task/1": "{0}",
    "round/1": "round {0}",
    "agent/3": "at ({0}, {1}), facing {2}",
    # ---- n-ary structures that would otherwise fall back to a labelled list
    "adjudicated/4": "trial {0}: {1} on {2} was {3}",
    "obj/4": "{0} is {1} at ({2}, {3})",
    "obs/3": "in block {0}, {1} = {2}",
    "round/3": "given {0}, {1} gave {2}",
    "item/4": "{0}: {1}, {2}, {3}",
    "stage/4": "stage {0} ({1}): {2}, {3}",
    "input/3": "case {0}, position {1}: {2}",
    "output/3": "case {0}, position {1}: {2}",
    "turn/3": "turn {0}: {1} {2}",
    "request/4": "at {1}, {2} requested priority {3} (message {0})",
    "response/3": "at {1}, the reply went to {2} (message {0})",
    "dim/4": "{0} has dimensions ({1}, {2}, {3})",
    "means/3": "{0} means {1} {2}",
    "cost/3": "{1} on {0} costs {2}",
    "require/3": "{1} must be {0} {2}",
    "attempt/4": "{0}: {1} at difficulty {2} was {3}",
    "module/4": "{0} is a {1} module for {2}, size {3}",
    "kb_rule/3": "{0} records that {1} implies {2}",
    "needs/3": "{0} needs {1} = {2}",
    "norm/5": "{0} (priority {1}): if {2} then {3} to {4}",
    "det/6": "{0} at ({2}, {3}), size {4}x{5}, confidence {1}",
    "event/4": "{0}: {1}, {2}, {3}",
    "schema/2": "{0}: {1}",
    "equation/2": "{0}: {1}",
    "resolve_by/1": "resolve by {0}",
    "color/1": "coloured {0}",
    "shape/1": "shaped {0}",
    "at_start/1": "{0} at the start",
    "at_end/1": "{0} at the end",
    "apply/2": "apply({0}, {1})",
    "multiset/0": "its multiset of elements",
    "order/0": "its order",
    "length/0": "its length",
}

# --------------------------------------------------------------------------
# questions
# --------------------------------------------------------------------------
def _quant(lang, terms):
    """``(quant all yellow)`` — one construction per quantifier.

    A single template cannot serve all four: "some of the objects are red,
    true or false?" answers yes/no, but "are some of the objects red?" is the
    question the answer set actually matches, and each quantifier wants its own
    shape.
    """
    q, what = (t.value for t in terms[:2])
    adj = lang.text(what)
    return {
        "all": f"are all of the objects {adj}?",
        "some": f"is any object {adj}?",
        "none": f"is no object {adj}?",
        "exactly_two": f"are exactly two objects {adj}?",
    }.get(str(q), f"are {lang.lexicon.quantifiers.get(str(q), str(q))} "
                  f"of the objects {adj}?")


_QUERY_TEMPLATES = {
    "which": "which object is the {0} {1}?",
    "which_color": "what colour does {0} mean?",
    "classify": "is {0} high or low?",
    "at": "what is the symbol at position {0}?",
    "accept": "is the string {0} in the language?",
    "balanced": "is the string balanced?",
    "palindrome": "is the string a palindrome?",
    "max_depth": "how deeply does the string nest?",
    "first_leaf": "what is the first leaf of the tree?",
    "next": "what comes next?",
    "quant": _quant,
    "the": "find the {0} object {1}.",
    "find": "find the {0} object.",
    "value_of": "what is {0} bound to?",
    "unify": "what does {0} unify with?",
    "holds": "does {0} hold of {1}?",
    "answer": "what is the answer?",
    "who": "who {0} {1}?",
    "how_many": "how many {0} {1}?",
    "resolve_query_in": "answer the question in the {0} half.",
    # heads that are verbs or prepositional phrases rather than noun phrases:
    # left to the fallback they come out as "what is the refers to for she?"
    "act_on": "what should be done about {0}?",
    "aligns_with": "what does {0} align with?",
    "believes_ball_in": "where does {0} believe the ball is?",
    "color_at": "what colour is at position {0}?",
    "corresponds_to": "what corresponds to {0}?",
    "count_admissible_instantiations": "how many instantiations are admissible?",
    "count_readings": "how many readings does {0} have?",
    "has": "does {0} have {1}?",
    "holds_in_target": "does {0} {1} hold in the target domain?",
    "means": "what does {1} mean at time {0}?",
    "method_achieving": "which method achieves {0}?",
    "more_than": "are there more {0} than {1}?",
    "most_reliable_in": "who is most reliable on {0}?",
    "most_salient": "which {0} is most salient?",
    "none": "are none of them {0}?",
    "nth_output": "what is output {1} for {0}?",
    "output_for_input": "what does the program output for {0}?",
    "pivotal_for": "which event is pivotal for {0}?",
    "predict": "what do you predict at {0}?",
    "predictively_closed": "which level is predictively closed?",
    "preserves": "which transformation preserves {0}?",
    "run": "what does {0} evaluate to after {1} steps?",
    "refers_to": "what does {0} refer to?",
    "refutes_the_law": "which observation refutes the law?",
    "restores_consistency": "what restores consistency after {0}?",
    "reversed_at": "what is at position {0} of the reversal?",
    "room_of": "which room is {0} in at time {1}?",
    "same_entity": "are {0} and {1} the same entity?",
    "select": "which objects are {0}?",
    "status_at": "what is the status at {0}?",
    "sufficient_explanation_of": "what sufficiently explains {0}?",
    "target_word_at": "what is word {1} of the translation of {0}?",
    "verb_of": "what is the verb belonging to {0}?",
    "which_goal_to_abandon": "which goal should be abandoned?",
    "which_goal_to_drop": "which goal should be dropped?",
    "which_object": "which object is to the {0}?",
    "will_succeed": "will {0} succeed at {1} with budget {2}?",
    "winning_move_at": "what is the winning move at {0}?",
    "word_for": "what is the word for {1} in generation {0}?",
    "works_in_city": "which city does {0} work in?",
}

# --------------------------------------------------------------------------
_VOCAB, _RAW = load_vocabulary("english")

ENGLISH = Lexicon(
    definite="the", indefinite="a", indefinite_before_vowel="an",
    copula_sg="is", copula_pl="are", negation="not",
    conjunction="and", disjunction="or", yes="yes", no="no", of="of",
    operators=_OPERATORS,
    prepositions=_PREPOSITIONS,
    quantifiers=_QUANTIFIERS,
    prefix_operators=_PREFIX_OPERATORS,
    field_intros=_FIELD_INTROS,
    predicate_templates=_PREDICATE_TEMPLATES,
    query_templates=_QUERY_TEMPLATES,
    # the inflected material the agreement and binding lessons build from
    verbs=("chased", "praised", "watched", "avoided", "greeted", "followed"),
    intransitive_verbs=("left", "smiled", "waited", "returned", "slept", "laughed"),
    adverbs=("yesterday", "quietly", "again", "twice"),
    noun_forms=(("key", "keys"), ("dog", "dogs"), ("author", "authors"),
                ("farmer", "farmers"), ("book", "books"), ("pilot", "pilots")),
    agreement_forms=(("opens", "open"), ("arrives", "arrive"), ("works", "work"),
                     ("fails", "fail"), ("moves", "move"), ("waits", "wait")),
    pronouns={"f": "she", "m": "he"},
    name_gender={"alice": "f", "bob": "m", "carol": "f",
                 "dave": "m", "erin": "f", "frank": "m"},
    preposition_words=("near", "beside", "under", "behind", "by"),
    synonyms={**SYNONYMS, **SHAPE_SYNONYMS},
    vocabulary=_VOCAB,
)

_WH = ("which", "what", "who", "whom", "whose", "where", "when", "why", "how")
_AUX = ("is", "are", "was", "were", "does", "do", "did", "can", "should", "will", "must")


class English(NaturalLanguage):
    """English prose. The default, and the reference implementation of a pack."""

    grammar_notes = (
        "determiner, adjectives, then noun",
        "indefinite article by phonology (a/an)",
        "questions by fronting a wh-word",
        "regular -s/-es/-ies plural, with the vocabulary carrying irregulars",
        "no grammatical gender, so no agreement to get wrong",
    )

    def sentence(self, text, end=None):
        return _A_BEFORE_VOWEL.sub("an ", super().sentence(text, end))

    def __init__(self, *, code: str = "english", name: str = "English",
                 description: str = "English prose; the default presentation.",
                 synonym_scope: str = "none"):
        super().__init__(code=code, name=name, lexicon=ENGLISH,
                         description=description, synonym_scope=synonym_scope)

    def generic_question(self, head, args):
        """English forms a question by fronting a wh-word.

        A head that already begins with one, or with an auxiliary, stands as it
        is. A head ending in a preposition becomes ``what is the X of Y?``.
        Everything else is a *name for a thing*, and becomes a request for that
        thing: ``what is the X (for Y)?``.
        """
        head_words = head.replace("_", " ").strip()
        joined = " ".join(args)
        first = head_words.split(" ", 1)[0].lower()
        if first in _WH or first in _AUX:
            return f"{head_words} {joined}"
        if head_words.endswith((" of", " for")):
            return f"what is the {head_words} {joined}"
        tail = f" for {joined}" if joined else ""
        return f"what is the {head_words}{tail}"


class EnglishSynonym(English):
    """English with the question's content words held out of the training vocabulary."""

    def __init__(self):
        super().__init__(
            code="english_synonym", name="English (held-out synonyms)",
            description=("English prose whose question uses near-synonyms the "
                         "learner has not met in training."),
            synonym_scope="query")
