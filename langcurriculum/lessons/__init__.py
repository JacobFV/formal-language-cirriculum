"""Every lesson, one module each, grouped into the curriculum's sections."""

from __future__ import annotations

from . import s01_symbols_and_grounding
from . import s02_compositional_semantics
from . import s03_language_as_action
from . import s04_analogy_causality_and_programs
from . import s05_ontology_and_representation
from . import s06_scientific_induction
from . import s07_mathematics_and_formal_reasoning
from . import s08_epistemics_and_argument
from . import s09_problem_formulation
from . import s10_reflective_computation
from . import s11_protocols_and_institutions
from . import s12_narrative_and_identity
from . import s13_self_modeling
from . import s14_open_ended_epistemology
from . import s15_values_and_goals
from . import s16_civilization_scale
from . import s17_capstones
from . import s18_supplementary

SECTIONS = (
    s01_symbols_and_grounding,
    s02_compositional_semantics,
    s03_language_as_action,
    s04_analogy_causality_and_programs,
    s05_ontology_and_representation,
    s06_scientific_induction,
    s07_mathematics_and_formal_reasoning,
    s08_epistemics_and_argument,
    s09_problem_formulation,
    s10_reflective_computation,
    s11_protocols_and_institutions,
    s12_narrative_and_identity,
    s13_self_modeling,
    s14_open_ended_epistemology,
    s15_values_and_goals,
    s16_civilization_scale,
    s17_capstones,
    s18_supplementary,
)

#: every lesson class, in curriculum order
LESSON_CLASSES = tuple(c for _s in SECTIONS for c in _s.LESSONS)

__all__ = ["SECTIONS", "LESSON_CLASSES"] + [_s.__name__.rsplit(".", 1)[-1] for _s in SECTIONS]
