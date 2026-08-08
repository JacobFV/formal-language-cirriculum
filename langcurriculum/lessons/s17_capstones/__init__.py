"""Ultimate transfer and open-world capstones."""

from __future__ import annotations

from .universal_interface_transfer import UniversalInterfaceTransfer
from .unknown_game import UnknownGame
from .symbolic_generalist import SymbolicGeneralist
from .open_world_research_agent import OpenWorldResearchAgent

SECTION = "xvii"
SECTION_TITLE = "ultimate transfer and open-world capstones"

LESSONS = (
    UniversalInterfaceTransfer,
    UnknownGame,
    SymbolicGeneralist,
    OpenWorldResearchAgent,
)

__all__ = ["UniversalInterfaceTransfer", "UnknownGame", "SymbolicGeneralist", "OpenWorldResearchAgent", "LESSONS", "SECTION", "SECTION_TITLE"]
