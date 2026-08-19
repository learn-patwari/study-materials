"""Which pose Pattu strikes, and when.

This is the behaviour table for the mascot — edit it to change *when* Pattu
changes pose. How the change is drawn (fades, timers) lives in
``mascot_animator.py``; the look of the chat window lives in ``theme.py``.

Deliberately free of PyQt imports so the mapping can be unit-tested without a
display attached.
"""
from __future__ import annotations

from enum import Enum


class MascotState(Enum):
    """A pose, and the frame in assets/mascot/ that draws it."""

    IDLE = "idle.png"
    GREETING = "greeting.png"
    THINKING = "thinking.png"
    WORKING = "working.png"
    EXPLAINING = "explaining.png"
    IDEA = "idea.png"
    SUCCESS = "success.png"
    CELEBRATING = "celebrating.png"
    READY = "ready.png"

    @property
    def filename(self) -> str:
        return self.value


# ── When each pose appears ────────────────────────────────────────────────────

# Orchestrator tool name -> pose held while that subagent runs. Every tool in
# core.orchestrator.TOOLS needs an entry; a test enforces it, so adding a tool
# without a pose fails the suite rather than silently freezing the mascot.
TOOL_STATES: dict[str, MascotState] = {
    "run_jira_agent": MascotState.WORKING,
    "run_bitbucket_agent": MascotState.WORKING,
    "bitbucket_inspect_repo": MascotState.IDEA,
    "confluence_create_page": MascotState.WORKING,
    "confluence_list_pages": MascotState.THINKING,
    "recall_memory": MascotState.THINKING,
}

# Poses that are a momentary reaction. They hold for STATE_HOLD_MS and then
# settle back to IDLE on their own. Anything not listed here stays until
# something else replaces it — THINKING and WORKING persist for as long as the
# work does.
TRANSIENT_STATES: frozenset[MascotState] = frozenset(
    {
        MascotState.GREETING,
        MascotState.SUCCESS,
        MascotState.CELEBRATING,
        MascotState.IDEA,
    }
)

# How long a transient pose holds before returning to IDLE.
STATE_HOLD_MS = 4_000

# While nothing is happening, the mascot drifts through these so it reads as
# alive rather than as a screenshot pinned to the desktop.
IDLE_CYCLE: tuple[MascotState, ...] = (
    MascotState.IDLE,
    MascotState.READY,
    MascotState.IDLE,
    MascotState.GREETING,
)


def state_for_tool(tool_name: str) -> MascotState:
    """Pose for a tool call, falling back to a generic busy pose."""
    return TOOL_STATES.get(tool_name, MascotState.WORKING)


# ── What Pattu says ───────────────────────────────────────────────────────────

# Lines the speech bubble can show for a given pose. A state with no entry
# here just shows the pose with no bubble. Add or edit lines freely — nothing
# else needs to change.
GREETING_MESSAGES: dict[MascotState, tuple[str, ...]] = {
    MascotState.GREETING: (
        "Hey! I'm Pattu 👋",
        "Ready when you are.",
        "Back online.",
    ),
    MascotState.THINKING: (
        "Let me think about that...",
        "Working it out.",
    ),
    MascotState.WORKING: (
        "On it.",
        "Running that now.",
    ),
    MascotState.IDEA: (
        "I think I found the cause.",
        "Got a lead on this one.",
    ),
    MascotState.SUCCESS: (
        "Done — take a look.",
        "All set.",
    ),
    MascotState.CELEBRATING: (
        "Daily brief is ready! 🎉",
        "Wrapped it all up.",
    ),
}


def greeting_for(state: MascotState, index: int = 0) -> str | None:
    """A line to show in the speech bubble for this pose, or None for silence.

    ``index`` picks among a repeated state's lines (e.g. pass a counter) so
    reacting to the same state twice in a row doesn't repeat the same line.
    """
    lines = GREETING_MESSAGES.get(state)
    if not lines:
        return None
    return lines[index % len(lines)]
