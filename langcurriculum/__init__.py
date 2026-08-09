"""A language curriculum: 170 lessons, procedurally generated, exactly graded.

The premise is that "language ability" is not one number obtained by predicting
tokens. It is a profile over capabilities that build on each other — reference,
equivalence, discrimination, sequence memory, finite-state syntax, recursion,
parsing, variable binding, unification, quantification, compositional reference,
and upward from there through causality, ontology, scientific induction, proof,
argument, self-modeling and value inference.

Every lesson is a **generator**, not a dataset. An episode is a pure function of
a seed: the vocabulary is invented per episode, the grammar or ontology or proof
calculus is sampled fresh, and the answer is computed from the construction
rather than annotated by anyone. Two consequences follow, and they are the whole
reason the resource exists:

* **An evaluation set cannot have been trained on.** It did not exist until you
  asked for it. There is no contamination question to argue about.
* **Every score has a floor.** The answer set travels with the episode, so
  "what does knowing nothing get?" is computable per lesson, and an accuracy is
  never reported without it.

Everything crossing this API is plain text or plain data — strings, dicts,
lists, numbers. Point it at anything that maps a string to a string.

    >>> import langcurriculum as lc
    >>> ex = lc.get("symbol_grounding").example(seed=0)
    >>> ex.prompt.splitlines()[-1]
    'Reply with the answer only.'
    >>> report = lc.evaluate(lambda prompt: "o0", n=20)   # doctest: +SKIP
    >>> print(report.table())                             # doctest: +SKIP
"""

from __future__ import annotations

from .dataset import export, iter_records, read_jsonl, splits, write_jsonl
from .evaluate import (LessonResult, Report, TextAgent, constant_agent, evaluate,
                       evaluate_lesson, random_agent)
from .lesson import AXES, CORE_AXES, EXTENDED_AXES, Example, Lesson, LessonNotImplemented
from .registry import (REGISTRY, SECTION_TITLES, all_lessons, by_capability, by_section,
                       get, lesson_ids, numbered, resolve, sections, supplementary)
from .scoring import extract_choice, normalize, score
from .languages import (DEFAULT_LANGUAGE, LANGUAGES, Language, Lexicon,
                        get_language, language_codes, languages,
                        register_language)
from .verify import verify_all, verify_lesson

__version__ = "0.1.0"

#: lessons in the numbered curriculum
N_NUMBERED = 170
#: lessons in the registry, including the supplementary ones
N_REGISTERED = 180

__all__ = [
    "__version__", "N_NUMBERED", "N_REGISTERED",
    # lessons
    "Lesson", "Example", "AXES", "CORE_AXES", "EXTENDED_AXES", "LessonNotImplemented",
    # languages
    "DEFAULT_LANGUAGE", "LANGUAGES", "Language", "Lexicon",
    "get_language", "language_codes", "languages", "register_language",
    # registry
    "REGISTRY", "SECTION_TITLES", "all_lessons", "get", "lesson_ids", "sections",
    "by_section", "by_capability", "numbered", "supplementary", "resolve",
    # evaluation
    "evaluate", "evaluate_lesson", "Report", "LessonResult", "TextAgent",
    "random_agent", "constant_agent", "score", "normalize", "extract_choice",
    # datasets
    "iter_records", "write_jsonl", "read_jsonl", "export", "splits",
    # verification
    "verify_lesson", "verify_all",
]
