"""Drawing the mascot: cross-fades, per-pose animation loops, idle drift, and
the breathing bob.

Pure animation. It knows nothing about Jira, chat or tool calls — it is handed
a :class:`MascotState` and works out how to get there smoothly. Change *when*
poses appear in ``mascot_states.py``; change *how* they appear with the
constants below.

Each pose can be a single static image or a full animation loop (a directory
of frames under ``assets/mascot_frames/<state>/`` — see ``tools/prepare_assets.py``).
Switching poses always cross-fades into the target's first frame; once that
settles, if the pose has a loop, it starts playing on its own timer until the
next state change interrupts it.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QPainter, QPixmap

from gui.assets import animation_frame_paths, asset_path
from gui.mascot_states import (
    IDLE_CYCLE,
    STATE_HOLD_MS,
    TRANSIENT_STATES,
    MascotState,
)

# ── Timing ────────────────────────────────────────────────────────────────────

FADE_DURATION_MS = 220   # length of a pose change
FADE_STEPS = 14          # frames drawn during it; higher is smoother, costlier
IDLE_CYCLE_MS = 9_000    # gap between ambient pose changes when nothing is happening
BOB_PERIOD_MS = 3_200    # one full breathing cycle
BOB_PIXELS = 3           # vertical travel of the bob; 0 disables it
BOB_INTERVAL_MS = 50     # bob redraw rate

# Playback rate for a pose's own animation loop (e.g. the typing motion while
# WORKING, the wave while GREETING) once a cross-fade into it has settled.
SEQUENCE_FRAME_MS = 70


class MascotAnimator(QObject):
    """Drives the pixmap shown by a mascot widget.

    The widget supplies ``set_frame(pixmap)`` and ``set_bob_offset(dy)``; this
    class decides what they receive and when.
    """

    def __init__(self, widget, mascot_size: tuple[int, int] | None = None):
        super().__init__(widget)
        self._widget = widget
        self._frames: dict[MascotState, QPixmap] = {}
        self._sequences: dict[MascotState, list[QPixmap]] = {}
        self._state = MascotState.IDLE
        self._idle_index = 0
        self._seq_index = 0

        self._fade_step = 0
        self._fade_from: QPixmap | None = None
        self._fade_to: QPixmap | None = None

        self._load_frames(mascot_size)
        self._load_sequences(mascot_size)

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(max(1, FADE_DURATION_MS // FADE_STEPS))
        self._fade_timer.timeout.connect(self._advance_fade)

        self._sequence_timer = QTimer(self)
        self._sequence_timer.setInterval(SEQUENCE_FRAME_MS)
        self._sequence_timer.timeout.connect(self._advance_sequence)

        self._revert_timer = QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(lambda: self.set_state(MascotState.IDLE))

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(IDLE_CYCLE_MS)
        self._idle_timer.timeout.connect(self._advance_idle)

        self._bob_timer = QTimer(self)
        self._bob_timer.setInterval(BOB_INTERVAL_MS)
        self._bob_timer.timeout.connect(self._advance_bob)
        self._bob_elapsed = 0

        if self._frames:
            self._widget.set_frame(self._frames[MascotState.IDLE])

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _load_frames(self, mascot_size: tuple[int, int] | None) -> None:
        """Load every pose once up front so a change never touches the disk."""
        for state in MascotState:
            pixmap = QPixmap(asset_path("mascot", state.filename))
            if pixmap.isNull():
                continue
            if mascot_size:
                pixmap = pixmap.scaled(
                    *mascot_size,
                    aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                    transformMode=Qt.TransformationMode.SmoothTransformation,
                )
            self._frames[state] = pixmap

    def _load_sequences(self, mascot_size: tuple[int, int] | None) -> None:
        """Load each pose's full animation, if one was prepared for it.

        A state with no ``mascot_frames/<state>/`` directory just plays as a
        single static pose, same as before — sequences are additive.
        """
        for state in MascotState:
            paths = animation_frame_paths(state.filename.removesuffix(".png"))
            if not paths:
                continue
            frames = []
            for path in paths:
                pixmap = QPixmap(path)
                if pixmap.isNull():
                    continue
                if mascot_size:
                    pixmap = pixmap.scaled(
                        *mascot_size,
                        aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                        transformMode=Qt.TransformationMode.SmoothTransformation,
                    )
                frames.append(pixmap)
            if frames:
                self._sequences[state] = frames
                # Keep the poster frame and the sequence's own first frame in
                # sync, so a cross-fade lands exactly where the loop starts.
                self._frames[state] = frames[0]

    @property
    def has_frames(self) -> bool:
        return bool(self._frames)

    @property
    def frame_size(self) -> tuple[int, int]:
        if not self._frames:
            return (0, 0)
        any_frame = next(iter(self._frames.values()))
        return (any_frame.width(), any_frame.height())

    def start(self) -> None:
        self._idle_timer.start()
        if BOB_PIXELS:
            self._bob_timer.start()
        self._start_sequence_if_available()

    def stop(self) -> None:
        for timer in (
            self._idle_timer,
            self._bob_timer,
            self._fade_timer,
            self._revert_timer,
            self._sequence_timer,
        ):
            timer.stop()

    # ── State changes ─────────────────────────────────────────────────────────

    def set_state(self, state: MascotState) -> None:
        """Cross-fade to a pose. Transient poses revert to idle by themselves."""
        if state not in self._frames or state is self._state:
            return

        self._sequence_timer.stop()
        self._fade_from = self._frames[self._state]
        self._fade_to = self._frames[state]
        self._state = state
        self._fade_step = 0
        self._fade_timer.start()

        # Restart the drift clock so a full interval always separates pose
        # changes — otherwise the mascot can drift right after reacting.
        self._idle_timer.start()

        self._revert_timer.stop()
        if state in TRANSIENT_STATES:
            self._revert_timer.start(STATE_HOLD_MS)

    @property
    def state(self) -> MascotState:
        return self._state

    # ── Animation steps ───────────────────────────────────────────────────────

    def _advance_fade(self) -> None:
        self._fade_step += 1
        progress = min(1.0, self._fade_step / FADE_STEPS)

        if progress >= 1.0 or self._fade_from is None or self._fade_to is None:
            self._fade_timer.stop()
            if self._fade_to is not None:
                self._widget.set_frame(self._fade_to)
            self._start_sequence_if_available()
            return

        self._widget.set_frame(self._blend(self._fade_from, self._fade_to, progress))

    def _start_sequence_if_available(self) -> None:
        """Once a cross-fade settles, start looping that pose's own animation."""
        if self._state in self._sequences:
            self._seq_index = 0
            self._sequence_timer.start()

    def _advance_sequence(self) -> None:
        frames = self._sequences.get(self._state)
        if not frames:
            self._sequence_timer.stop()
            return
        self._seq_index = (self._seq_index + 1) % len(frames)
        self._widget.set_frame(frames[self._seq_index])

    @staticmethod
    def _blend(before: QPixmap, after: QPixmap, progress: float) -> QPixmap:
        """Composite two frames at the given cross-fade progress."""
        canvas = QPixmap(before.size())
        canvas.fill(Qt.GlobalColor.transparent)  # fill() defaults to white
        painter = QPainter(canvas)
        painter.setOpacity(1.0 - progress)
        painter.drawPixmap(0, 0, before)
        painter.setOpacity(progress)
        painter.drawPixmap(0, 0, after)
        painter.end()
        return canvas

    def _advance_idle(self) -> None:
        """Drift to the next ambient pose, but never interrupt real activity."""
        if self._state not in (MascotState.IDLE, *IDLE_CYCLE):
            return
        self._idle_index = (self._idle_index + 1) % len(IDLE_CYCLE)
        next_state = IDLE_CYCLE[self._idle_index]
        if next_state is not self._state:
            self.set_state(next_state)

    def _advance_bob(self) -> None:
        self._bob_elapsed = (self._bob_elapsed + BOB_INTERVAL_MS) % BOB_PERIOD_MS
        phase = 2 * math.pi * self._bob_elapsed / BOB_PERIOD_MS
        self._widget.set_bob_offset(round(math.sin(phase) * BOB_PIXELS))
