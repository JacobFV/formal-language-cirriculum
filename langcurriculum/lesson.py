"""What a lesson is, and what one episode of it looks like.

A lesson is a **procedural generator**, not a dataset. An episode is a pure
function of the seed it is handed: the same seed always yields the same
question, and two different seeds yield two different worlds. That is the
property the whole resource rests on, because it means an evaluation set is
never a held-out sample of something a model might have seen — it is a world
that did not exist until the evaluator asked for it.

It also means the ground truth is *computed*, never annotated. The generator
invents the grammar, the ontology, the causal graph or the proof calculus, and
then decides the answer by reading its own construction. There is no labeller
to disagree with.

Each lesson carries the vocabulary of legal answers for the episode, so scoring
is exact and a floor baseline is well defined: a uniform guesser over that
vocabulary is what "knowing nothing" scores, and any lesson whose floor is not
comfortably below 1.0 is not measuring anything. See :mod:`langcurriculum.verify`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Iterator, Mapping, Sequence

from ._structure import Term, sexpr, to_json
from ._support.extra import ACTIVE_LANGUAGE
from .languages import DEFAULT_LANGUAGE, Language, get_language

__all__ = ["Lesson", "Example", "AXES", "CORE_AXES", "EXTENDED_AXES",
           "LessonNotImplemented", "as_text"]

#: The eight core difficulty axes every lesson declares a position on, so that a
#: result is a profile over axes rather than a single number.
CORE_AXES = ("lexical_novelty", "grammar_complexity", "recursion_depth", "compositional_depth",
             "discourse_horizon", "world_complexity", "ambiguity", "reasoning_depth")

#: Axes introduced by the later sections, where the core eight do not say what
#: makes a lesson hard. ``anytime_reasoning`` is not deep or ambiguous; it is
#: hard because the budget runs out, and that deserves its own dimension rather
#: than being folded into ``reasoning_depth``.
EXTENDED_AXES = ("uncertainty", "adversariality", "planning_horizon",
                 "representation_freedom", "computational_budget", "ontology_novelty")

#: Every axis a lesson may declare.
AXES = CORE_AXES + EXTENDED_AXES


class LessonNotImplemented(NotImplementedError):
    """Raised by a lesson that is specified but deliberately not generated.

    Exactly one lesson is in this state. It is kept in the registry, with its
    reasoning attached, rather than quietly dropped: a specification that cannot
    yet be graded honestly is still part of the curriculum's claim.
    """


def as_text(x: Any) -> str:
    """Render an answer or a choice as the plain text a caller will compare."""
    if isinstance(x, Term):
        return sexpr(x)
    if isinstance(x, bool):
        return "yes" if x else "no"
    return str(x)


@dataclass(frozen=True)
class Example:
    """One generated episode, entirely as plain data.

    ``observation`` is the question as rendered text — English prose by default.
    ``prompt`` is that plus a one-line instruction naming the legal answers,
    which is what you hand a text agent. ``answer`` is the exact gold string,
    and ``choices`` is the answer vocabulary for *this* episode — often invented
    in the episode itself, so it varies from one seed to the next.
    """

    lesson_id: str
    seed: int
    language: str
    observation: str
    prompt: str
    answer: str
    choices: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"lesson_id": self.lesson_id, "seed": self.seed, "language": self.language,
                "observation": self.observation, "prompt": self.prompt,
                "answer": self.answer, "choices": list(self.choices),
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Example":
        return cls(lesson_id=d["lesson_id"], seed=int(d["seed"]), language=d["language"],
                   observation=d["observation"], prompt=d["prompt"], answer=d["answer"],
                   choices=tuple(d["choices"]), metadata=dict(d.get("metadata") or {}))


class Lesson:
    """Base class. One subclass per lesson, one module per subclass.

    Subclasses set the class attributes below and provide ``generate``, a pure
    function of a :class:`random.Random` returning
    ``(observation, choices, answer, hidden)``.

    ``hidden`` is the part of the world the generator knows and the agent is not
    shown — the grammar it sampled, the boundary it drew, the lexicon it
    invented. It travels in ``Example.metadata["hidden"]`` for the evaluator's
    benefit and never appears in the prompt.
    """

    #: stable snake_case identifier, unique across the registry
    id: ClassVar[str] = ""
    #: position in the curriculum's numbering, 1-170, or ``None`` for the
    #: supplementary lessons that are not part of that sequence
    number: ClassVar[int | None] = None
    #: difficulty level as declared by the lesson itself
    level: ClassVar[int] = 0
    #: section key, e.g. ``"iv"``, or ``"supplementary"``
    section: ClassVar[str] = ""
    #: human-readable section title
    section_title: ClassVar[str] = ""
    #: one line saying what the lesson teaches
    teaches: ClassVar[str] = ""
    #: capability tags, for grouping results by ability rather than by lesson
    capabilities: ClassVar[tuple[str, ...]] = ()
    #: position on the difficulty axes; keys are drawn from :data:`AXES`
    axes: ClassVar[Mapping[str, int]] = {}
    #: a fixed answer vocabulary, when the lesson has one across all episodes
    answers: ClassVar[Sequence[Any] | None] = None
    #: ``implemented`` or ``spec``
    status: ClassVar[str] = "implemented"
    #: why, when ``status`` is not ``implemented``
    note: ClassVar[str] = ""

    generate: ClassVar[Callable[[random.Random], tuple[Term, Sequence[Any], Any, dict[str, Any]]]]

    # ---- generation -------------------------------------------------
    def example(self, seed: int = 0, *,
                language: str | Language = DEFAULT_LANGUAGE) -> Example:
        """Generate one episode. The same ``seed`` always gives the same episode.

        ``language`` selects the pack the episode is read in and defaults to
        English prose. See :mod:`langcurriculum.languages`.
        """
        lang = get_language(language)
        if self.status != "implemented":
            raise LessonNotImplemented(f"{self.id}: {self.note}")
        # The morphology lessons draw their inflected material from the pack
        # the episode will be read in, so the generator has to know which that
        # is. It was read once at import from the default language, which is
        # why an agreement lesson asked for in Russian came out in English.
        token = ACTIVE_LANGUAGE.set(lang.code)
        try:
            obs, choices, answer, hidden = type(self).generate(random.Random(seed))
        finally:
            ACTIVE_LANGUAGE.reset(token)
        raw_opts = tuple(as_text(c) for c in choices)
        opts, answer, collapsed = _translate_options(lang, raw_opts, as_text(answer))
        observation = lang.render(obs)
        return Example(
            lesson_id=self.id, seed=seed, language=lang.code,
            observation=observation, prompt=lang.prompt(observation, opts),
            answer=answer, choices=opts,
            metadata={"number": self.number, "level": self.level, "section": self.section,
                      "teaches": self.teaches, "capabilities": list(self.capabilities),
                      "axes": dict(self.axes), "hidden": _plain(hidden),
                      **({"untranslated_options": True} if collapsed else {})},
        )

    def examples(self, n: int = 100, *, seed0: int = 0,
                 language: str | Language = DEFAULT_LANGUAGE) -> Iterator[Example]:
        """Generate ``n`` consecutive episodes starting from ``seed0``."""
        for i in range(n):
            yield self.example(seed0 + i, language=language)

    def structured(self, seed: int = 0) -> dict[str, Any]:
        """The episode as plain JSON-able data rather than as text.

        For callers that would rather walk the structure than parse the
        s-expression. Still no library types: dicts, lists, strings, numbers.
        """
        if self.status != "implemented":
            raise LessonNotImplemented(f"{self.id}: {self.note}")
        obs, choices, answer, hidden = type(self).generate(random.Random(seed))
        return {"lesson_id": self.id, "seed": seed, "observation": to_json(obs),
                "choices": [as_text(c) for c in choices], "answer": as_text(answer),
                "hidden": _plain(hidden)}

    # ---- metadata ----------------------------------------------------
    def info(self) -> dict[str, Any]:
        """Everything the lesson declares about itself, as plain data."""
        return {"id": self.id, "number": self.number, "level": self.level,
                "section": self.section, "section_title": self.section_title,
                "teaches": self.teaches, "capabilities": list(self.capabilities),
                "axes": dict(self.axes), "status": self.status, "note": self.note,
                "fixed_answers": [as_text(a) for a in self.answers] if self.answers else None,
                "description": (type(self).generate.__doc__ or "").strip()}

    @property
    def description(self) -> str:
        """The generator's own account of what it builds."""
        return (type(self).generate.__doc__ or "").strip()

    def __repr__(self) -> str:
        n = f"#{self.number} " if self.number else ""
        return f"<Lesson {n}{self.id}: {self.teaches}>"


def _translate_options(lang, options: Sequence[str], answer: str) -> tuple[tuple[str, ...], str, bool]:
    """Render the answer set in the prompt's language — unless that collapses it.

    The options have to be in the same language as the prompt, or the episode
    asks its question in one language and offers its answers in another. But a
    few lessons are *about* morphology, and their answer set is a set of
    inflected English forms: ``opens`` versus ``open``. A language without that
    inflection translates both to one word, and the episode stops being
    answerable at all.

    An answer set is a paradigm, so it is rendered whole or not at all. The
    translation is applied only when the pack knows **every** option and the
    result stays injective. A set of object ids or nonce forms is known to
    nobody and stays as it is, which is right — those are not words. A set of
    inflected English forms is known only in part, and stays as it is too, with
    ``metadata["untranslated_options"]`` recording that it did: a prompt whose
    options are visibly in another language is a much smaller problem than a
    prompt with two identical options and one correct answer.
    """
    # Ask the language, not one particular kind of lexicon. The old question
    # was put to `lang.lexicon.vocabulary`, which a derived language does not
    # have, so every one of them answered "no" to every option and offered
    # English answers against translated evidence.
    known = [lang.knows(o) for o in options]
    if not options or not all(known):
        return tuple(options), answer, any(known)
    translated = tuple(lang.token(o) for o in options)
    if len(set(translated)) != len(set(options)):
        return tuple(options), answer, True
    return translated, lang.token(answer), False


def _plain(d: Any) -> Any:
    """Coerce a hidden-state mapping to something ``json.dumps`` will accept."""
    if isinstance(d, Mapping):
        return {str(k): _plain(v) for k, v in d.items()}
    if isinstance(d, (list, tuple, set, frozenset)):
        return [_plain(x) for x in d]
    if isinstance(d, Term):
        return sexpr(d)
    if isinstance(d, (int, float, str, bool)) or d is None:
        return d
    return str(d)
