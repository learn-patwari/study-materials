"""Tests for the autonomous-wander behaviour.

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


class RoamWidgetStub(QObject):
    """Stands in for MascotWidget — records what the roamer tells it to do.

    A QObject because the roamer parents itself to the widget, as the real
    QWidget collaborator allows.
    """

    def __init__(self, x=100, y=800, width=240, state=MascotState.IDLE):
        super().__init__()
        self._x = x
        self._y = y
        self._width = width
        self._state = state
        self.moves: list[tuple[int, int]] = []
        self.facing_calls: list[bool] = []
        self.reacted = False

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._width

    def current_state(self):
        return self._state

    def anchor_at(self, x, y):
        self._x, self._y = x, y
        self.moves.append((x, y))

    def set_facing_left(self, facing_left):
        self.facing_calls.append(facing_left)

    def react(self):
        self.reacted = True


@pytest.fixture
def widget(qt_app):
    return RoamWidgetStub()


@pytest.fixture
def roamer(qt_app, widget):
    from gui.mascot_roamer import MascotRoamer

    return MascotRoamer(widget)


class TestScheduling:
    def test_start_arms_the_schedule_timer(self, roamer):
        roamer.start()
        assert roamer._schedule_timer.isActive()

    def test_pause_stops_everything(self, roamer):
        roamer.start()
        roamer.pause()
        assert not roamer._schedule_timer.isActive()
        assert not roamer._walk_timer.isActive()
        assert not roamer.is_walking

    def test_resume_reschedules(self, roamer):
        roamer.pause()
        roamer.resume()
        assert roamer._schedule_timer.isActive()

    def test_paused_roamer_does_not_reschedule(self, roamer):
        roamer.pause()
        roamer._schedule_next()
        assert not roamer._schedule_timer.isActive()


class TestBeginWalk:
    def test_busy_state_defers_the_walk(self, roamer, widget):
        widget._state = MascotState.THINKING
        roamer._begin_walk()
        assert not roamer.is_walking
        assert roamer._schedule_timer.isActive()

    def test_idle_state_starts_walking(self, roamer, widget):
        widget._state = MascotState.IDLE
        roamer._begin_walk()
        assert roamer.is_walking
        assert roamer._walk_timer.isActive()

    def test_faces_the_direction_it_will_walk(self, roamer, widget):
        widget._x = 100
        roamer._target_x = 900  # force a rightward target via manual begin below
        widget._state = MascotState.IDLE
        roamer._begin_walk()
        # target was chosen randomly inside _begin_walk, but facing must match
        # the sign of (target - current x) that was actually picked.
        expected_left = roamer._target_x < 100
        assert widget.facing_calls[-1] == expected_left


class TestWalkTick:
    def test_moves_toward_the_target(self, roamer, widget):
        widget._x = 0
        roamer._target_x = 300
        roamer._walking = True
        roamer._walk_tick()
        assert widget.moves
        moved_x, _ = widget.moves[-1]
        assert 0 < moved_x <= 300

    def test_stops_within_step_of_target_and_may_wave(self, roamer, widget):
        widget._x = 298
        roamer._target_x = 300
        roamer._walking = True
        roamer._walk_timer.start()
        roamer._walk_tick()
        assert widget.moves[-1] == (300, widget.y())
        assert not roamer.is_walking
        assert not roamer._walk_timer.isActive()

    def test_a_started_task_interrupts_the_walk(self, roamer, widget):
        widget._x = 0
        roamer._target_x = 300
        roamer._walking = True
        roamer._walk_timer.start()
        widget._state = MascotState.WORKING
        roamer._walk_tick()
        assert not roamer.is_walking
        assert not roamer._walk_timer.isActive()
