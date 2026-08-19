"""Autonomous wandering — Pattu strolls the desktop like a classic desktop mascot.

While nothing is going on, the character occasionally picks a spot along the
screen and walks there, facing the direction it's moving, then settles and
sometimes waves. A drag or a real task (thinking, working, explaining) stops
it immediately — it never fights the user or looks like it's ignoring what
Pattu is actually doing.

Knows nothing about poses or fades (``mascot_animator.py``) or what a pose
means (``mascot_states.py``) — it only ever moves the widget and asks it what
state it's in.
"""
from __future__ import annotations

import random

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication

from gui.mascot_states import MascotState

# How long Pattu stays put before wandering to a new spot.
ROAM_MIN_INTERVAL_MS = 15_000
ROAM_MAX_INTERVAL_MS = 35_000

# Walking speed: pixels per tick, ticks per second.
WALK_STEP_PX = 3
WALK_TICK_MS = 16

# Stay clear of the very edges of the screen.
SCREEN_MARGIN_PX = 40

# Chance (0-1) of a little wave once a walk finishes.
WAVE_CHANCE = 0.4

# Real work in progress — never wander mid-task. Reactions like GREETING,
# SUCCESS or IDEA are brief and don't need to block wandering.
BUSY_STATES = frozenset({MascotState.THINKING, MascotState.WORKING, MascotState.EXPLAINING})


class MascotRoamer(QObject):
    """Owns the wander timers. ``widget`` just gets told where to move and how to face."""

    def __init__(self, widget):
        super().__init__(widget)
        self._widget = widget
        self._paused = False
        self._walking = False
        self._target_x = widget.x()

        self._schedule_timer = QTimer(self)
        self._schedule_timer.setSingleShot(True)
        self._schedule_timer.timeout.connect(self._begin_walk)

        self._walk_timer = QTimer(self)
        self._walk_timer.setInterval(WALK_TICK_MS)
        self._walk_timer.timeout.connect(self._walk_tick)

    def start(self) -> None:
        self._schedule_next()

    def pause(self) -> None:
        """Called while the user is dragging the mascot."""
        self._paused = True
        self._schedule_timer.stop()
        self._walk_timer.stop()
        self._walking = False

    def resume(self) -> None:
        """Called once the user lets go — picks wandering back up from here."""
        self._paused = False
        self._schedule_next()

    @property
    def is_walking(self) -> bool:
        return self._walking

    # ── Internals ────────────────────────────────────────────────────────────

    def _schedule_next(self) -> None:
        if self._paused:
            return
        delay = random.randint(ROAM_MIN_INTERVAL_MS, ROAM_MAX_INTERVAL_MS)
        self._schedule_timer.start(delay)

    def _is_free_to_wander(self) -> bool:
        return not self._paused and self._widget.current_state() not in BUSY_STATES

    def _begin_walk(self) -> None:
        if not self._is_free_to_wander():
            self._schedule_next()
            return

        screen = QApplication.primaryScreen().availableGeometry()
        low = screen.x() + SCREEN_MARGIN_PX
        high = screen.x() + screen.width() - self._widget.width() - SCREEN_MARGIN_PX
        if high <= low:
            self._schedule_next()
            return

        self._target_x = random.randint(low, high)
        self._widget.set_facing_left(self._target_x < self._widget.x())
        self._walking = True
        self._walk_timer.start()

    def _walk_tick(self) -> None:
        if not self._is_free_to_wander():
            self._stop_walk()
            self._schedule_next()
            return

        current_x = self._widget.x()
        remaining = self._target_x - current_x
        if abs(remaining) <= WALK_STEP_PX:
            self._widget.anchor_at(self._target_x, self._widget.y())
            self._stop_walk()
            if random.random() < WAVE_CHANCE:
                self._widget.react()
            self._schedule_next()
            return

        step = WALK_STEP_PX if remaining > 0 else -WALK_STEP_PX
        self._widget.anchor_at(current_x + step, self._widget.y())

    def _stop_walk(self) -> None:
        self._walk_timer.stop()
        self._walking = False
