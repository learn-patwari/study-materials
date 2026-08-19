"""Tests for the animation engine.

Needs PyQt6 and a Qt platform plugin. Skipped automatically where neither is
available, so the rest of the suite still runs headless.
"""
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 is only needed for the GUI")

from PyQt6.QtCore import QObject  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.mascot_states import MascotState  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        app = QApplication.instance() or QApplication([])
    except Exception as exc:  # missing libEGL and friends
        pytest.skip(f"no Qt platform available: {exc}")
    yield app


class RecordingWidget(QObject):
    """Stands in for MascotWidget — records what the animator sends it.

    A QObject because the animator parents itself to the widget for lifetime
    management, as the real QWidget collaborator allows.
    """

    def __init__(self):
        super().__init__()
        self.frames = []
        self.bob_offsets = []

    def set_frame(self, pixmap):
        self.frames.append(pixmap)

    def set_bob_offset(self, dy):
        self.bob_offsets.append(dy)


@pytest.fixture
def animator(qt_app):
    from gui.mascot_animator import MascotAnimator

    widget = RecordingWidget()
    instance = MascotAnimator(widget)
    if not instance.has_frames:
        pytest.skip("mascot frames not prepared")
    instance._widget_stub = widget
    return instance


class TestFrames:
    def test_loads_every_pose(self, animator):
        assert len(animator._frames) == len(list(MascotState))

    def test_all_frames_same_size(self, animator):
        sizes = {(p.width(), p.height()) for p in animator._frames.values()}
        assert len(sizes) == 1

    def test_starts_idle_and_paints(self, animator):
        assert animator.state is MascotState.IDLE
        assert animator._widget_stub.frames, "no initial frame was drawn"


class TestBlend:
    def test_midpoint_differs_from_both_ends(self, animator):
        before = animator._frames[MascotState.IDLE]
        after = animator._frames[MascotState.CELEBRATING]
        mid = animator._blend(before, after, 0.5).toImage()
        a, b = before.toImage(), after.toImage()

        differs_from_before = differs_from_after = 0
        for y in range(0, mid.height(), 7):
            for x in range(0, mid.width(), 7):
                differs_from_before += mid.pixel(x, y) != a.pixel(x, y)
                differs_from_after += mid.pixel(x, y) != b.pixel(x, y)

        assert differs_from_before and differs_from_after, "not a real cross-fade"

    def test_blend_keeps_transparency(self, animator):
        """A white fill here would show as a box around the mascot."""
        blended = animator._blend(
            animator._frames[MascotState.IDLE],
            animator._frames[MascotState.THINKING],
            0.5,
        )
        assert blended.hasAlphaChannel()
        assert blended.toImage().pixelColor(0, 0).alpha() == 0

    def test_blend_preserves_size(self, animator):
        before = animator._frames[MascotState.IDLE]
        assert animator._blend(before, animator._frames[MascotState.READY], 0.3).size() == before.size()


class TestStateChanges:
    def test_set_state_updates_state(self, animator):
        animator.set_state(MascotState.THINKING)
        assert animator.state is MascotState.THINKING

    def test_fade_settles_on_the_target(self, animator):
        animator.set_state(MascotState.WORKING)
        for _ in range(50):
            animator._advance_fade()
        final = animator._widget_stub.frames[-1].toImage()
        expected = animator._frames[MascotState.WORKING].toImage()
        assert final == expected

    def test_transient_pose_arms_the_revert(self, animator):
        animator.set_state(MascotState.CELEBRATING)
        assert animator._revert_timer.isActive()

    def test_busy_pose_does_not_revert(self, animator):
        """Work poses must last as long as the work does."""
        animator.set_state(MascotState.THINKING)
        assert not animator._revert_timer.isActive()

    def test_repeating_a_state_is_a_no_op(self, animator):
        animator.set_state(MascotState.THINKING)
        drawn = len(animator._widget_stub.frames)
        animator.set_state(MascotState.THINKING)
        assert len(animator._widget_stub.frames) == drawn


class TestIdleDrift:
    def test_drift_does_not_interrupt_work(self, animator):
        animator.set_state(MascotState.THINKING)
        animator._advance_idle()
        assert animator.state is MascotState.THINKING

    def test_drift_moves_on_when_quiet(self, animator):
        animator.set_state(MascotState.IDLE)
        animator._advance_idle()
        assert animator.state is not MascotState.IDLE

    def test_bob_reports_an_offset(self, animator):
        for _ in range(6):
            animator._advance_bob()
        assert animator._widget_stub.bob_offsets


class TestSequences:
    def test_sequences_load_when_prepared(self, animator):
        """This asset pack ships an animation for every pose."""
        if not animator._sequences:
            pytest.skip("no animation frames prepared — run tools/prepare_assets.py")
        assert len(animator._sequences) == len(MascotState)

    def test_poster_matches_sequence_first_frame(self, animator):
        for state, frames in animator._sequences.items():
            assert animator._frames[state].toImage() == frames[0].toImage()

    def test_settling_starts_the_loop(self, animator):
        if not animator._sequences:
            pytest.skip("no animation frames prepared")
        animator.set_state(MascotState.WORKING)
        for _ in range(FADE_STEPS_FOR_TEST):
            animator._advance_fade()
        assert animator._sequence_timer.isActive()

    def test_loop_cycles_through_every_frame(self, animator):
        if not animator._sequences:
            pytest.skip("no animation frames prepared")
        animator.set_state(MascotState.WORKING)
        for _ in range(FADE_STEPS_FOR_TEST):
            animator._advance_fade()

        frames = animator._sequences[MascotState.WORKING]
        seen_indices = set()
        for _ in range(len(frames) * 2):
            seen_indices.add(animator._seq_index)
            animator._advance_sequence()
        assert seen_indices == set(range(len(frames)))

    def test_new_state_change_stops_the_previous_loop(self, animator):
        if not animator._sequences:
            pytest.skip("no animation frames prepared")
        animator.set_state(MascotState.WORKING)
        for _ in range(FADE_STEPS_FOR_TEST):
            animator._advance_fade()
        assert animator._sequence_timer.isActive()

        animator.set_state(MascotState.THINKING)
        assert not animator._sequence_timer.isActive()


FADE_STEPS_FOR_TEST = 50  # comfortably more than FADE_STEPS, to fully settle
