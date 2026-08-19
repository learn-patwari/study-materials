"""Watch Pattu react to a scripted, fake conversation — no LLM, no Jira/
Bitbucket/Confluence credentials, no .env required.

Drives the real MascotWidget through the same states a live session would,
using canned "tool calls" instead of an actual orchestrator run. Useful for
checking new artwork or animation timing without wiring up real services.

    python tools/demo_mascot.py

Each step prints what it's simulating and calls the exact same
``mascot.set_state(...)`` the real chat window calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from gui.mascot_states import MascotState, state_for_tool
from gui.mascot_widget import MascotWidget

# (label to print, delay before it starts in ms, what it does)
SCRIPT = [
    ("Pattu launches", 0, lambda m: m.greet()),
    ("You: \"what's on my plate today?\"", 3_500, lambda m: m.set_state(MascotState.THINKING)),
    ("tool call: run_jira_agent", 6_000, lambda m: m.set_state(state_for_tool("run_jira_agent"))),
    ("tool call: bitbucket_inspect_repo", 9_000, lambda m: m.set_state(state_for_tool("bitbucket_inspect_repo"))),
    ("streaming the answer back", 12_000, lambda m: m.set_state(MascotState.EXPLAINING)),
    ("turn finished cleanly", 15_500, lambda m: m.set_state(MascotState.SUCCESS)),
    ("You: \"run my daily brief\"", 19_000, lambda m: m.set_state(MascotState.THINKING)),
    ("tool call: confluence_create_page", 21_500, lambda m: m.set_state(state_for_tool("confluence_create_page"))),
    ("daily brief complete", 25_000, lambda m: m.set_state(MascotState.CELEBRATING)),
    ("back to idle — script repeats", 29_500, lambda m: m.set_state(MascotState.IDLE)),
]

LOOP_EVERY_MS = 33_000


def run_step(mascot: MascotWidget, label: str, action) -> None:
    print(f"  [{label}]")
    action(mascot)


def main() -> int:
    app = QApplication(sys.argv)

    mascot = MascotWidget()
    mascot.show()

    print("Pattu demo — mock conversation, no credentials needed.")
    print("Close the mascot window (or Ctrl+C here) to stop.\n")

    def play_script() -> None:
        print("── replaying the scripted conversation ──")
        for label, delay, action in SCRIPT:
            QTimer.singleShot(delay, lambda l=label, a=action: run_step(mascot, l, a))

    play_script()
    loop_timer = QTimer()
    loop_timer.timeout.connect(play_script)
    loop_timer.start(LOOP_EVERY_MS)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
