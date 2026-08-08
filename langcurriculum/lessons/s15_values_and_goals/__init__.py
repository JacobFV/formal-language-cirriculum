"""Values and goal cognition."""

from __future__ import annotations

from .value_learning import ValueLearning
from .multi_objective_reasoning import MultiObjectiveReasoning
from .goal_inference import GoalInference
from .goal_revision import GoalRevision
from .goal_generation import GoalGeneration
from .reflective_goal_reasoning import ReflectiveGoalReasoning

SECTION = "xv"
SECTION_TITLE = "values and goal cognition"

LESSONS = (
    ValueLearning,
    MultiObjectiveReasoning,
    GoalInference,
    GoalRevision,
    GoalGeneration,
    ReflectiveGoalReasoning,
)

__all__ = ["ValueLearning", "MultiObjectiveReasoning", "GoalInference", "GoalRevision", "GoalGeneration", "ReflectiveGoalReasoning", "LESSONS", "SECTION", "SECTION_TITLE"]
