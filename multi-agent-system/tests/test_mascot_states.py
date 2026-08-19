"""Tests for the mascot state table and asset lookup.

Imports only pure-Python modules — no PyQt6, so these run headless.
"""
import os
import sys

import pytest

from gui.assets import animation_frame_paths, asset_exists, asset_path, assets_root
from gui.mascot_states import (
    GREETING_MESSAGES,
    IDLE_CYCLE,
    STATE_HOLD_MS,
    TOOL_STATES,
    TRANSIENT_STATES,
    MascotState,
    greeting_for,
    state_for_tool,
)

ICON_FILES = ["taskbar.png", "tray.png", "profile.png", "pattu.ico"]


class TestFramesExist:
    @pytest.mark.parametrize("state", list(MascotState))
    def test_every_state_has_a_frame(self, state):
        assert asset_exists("mascot", state.filename), (
            f"{state.name} points at missing assets/mascot/{state.filename} — "
            "run python tools/prepare_assets.py"
        )

    @pytest.mark.parametrize("icon", ICON_FILES)
    def test_icons_exist(self, icon):
        assert asset_exists("icons", icon)

    def test_frames_share_one_canvas(self):
        """Poses must be the same size or the mascot jumps when it animates."""
        from PIL import Image

        sizes = {
            Image.open(asset_path("mascot", s.filename)).size for s in MascotState
        }
        assert len(sizes) == 1, f"frames differ in size: {sizes}"

    def test_frames_are_transparent_pngs(self):
        from PIL import Image

        for state in MascotState:
            assert Image.open(asset_path("mascot", state.filename)).mode == "RGBA"


class TestAnimationFrames:
    """The SprintForge pack ships a full loop for every pose, not just a
    single pose — these confirm the pipeline extracted all of them cleanly."""

    @pytest.mark.parametrize("state", list(MascotState))
    def test_every_state_has_multiple_frames(self, state):
        name = state.filename.removesuffix(".png")
        frames = animation_frame_paths(name)
        if not frames:
            pytest.skip(f"no animation prepared for {state.name}")
        assert len(frames) > 1

    def test_sequence_frames_share_the_poster_canvas(self):
        """A frame that doesn't match the canvas would make the mascot jump
        mid-loop, not just between poses."""
        from PIL import Image

        for state in MascotState:
            name = state.filename.removesuffix(".png")
            frames = animation_frame_paths(name)
            if not frames:
                continue
            poster_size = Image.open(asset_path("mascot", state.filename)).size
            sizes = {Image.open(f).size for f in frames}
            assert sizes == {poster_size}, f"{state.name} frames differ from its poster size"

    def test_sequence_frames_are_transparent(self):
        """Regression: GIF's 1-bit transparency leaves later frames opaque
        black — the pipeline must be reading WEBP, not GIF."""
        from PIL import Image

        for state in MascotState:
            name = state.filename.removesuffix(".png")
            frames = animation_frame_paths(name)
            if not frames:
                continue
            for path in frames:
                img = Image.open(path)
                assert img.mode == "RGBA"
                # A frame that's fully opaque everywhere means transparency
                # was lost somewhere in the pipeline.
                alpha = img.getchannel("A")
                assert alpha.getextrema()[0] == 0, f"{path} has no transparent pixels"

    def test_frame_paths_are_sorted(self):
        frames = animation_frame_paths("working")
        if not frames:
            pytest.skip("no animation prepared for working")
        assert frames == sorted(frames)

    def test_missing_state_returns_empty(self):
        assert animation_frame_paths("does_not_exist") == []


class TestToolMapping:
    def test_every_orchestrator_tool_has_a_pose(self):
        """A new tool without a pose would silently freeze the mascot."""
        from core.orchestrator import TOOLS

        tool_names = {t["function"]["name"] for t in TOOLS}
        missing = tool_names - set(TOOL_STATES)
        assert not missing, f"no mascot pose mapped for: {sorted(missing)}"

    def test_no_mapping_for_unknown_tools(self):
        from core.orchestrator import TOOLS

        tool_names = {t["function"]["name"] for t in TOOLS}
        stale = set(TOOL_STATES) - tool_names
        assert not stale, f"TOOL_STATES maps tools that no longer exist: {sorted(stale)}"

    def test_all_mapped_values_are_states(self):
        assert all(isinstance(v, MascotState) for v in TOOL_STATES.values())

    def test_state_for_tool_known(self):
        assert state_for_tool("run_jira_agent") is MascotState.WORKING
        assert state_for_tool("bitbucket_inspect_repo") is MascotState.IDEA

    def test_state_for_tool_falls_back(self):
        assert state_for_tool("some_future_tool") is MascotState.WORKING


class TestStateTable:
    def test_transient_states_are_real_states(self):
        assert all(isinstance(s, MascotState) for s in TRANSIENT_STATES)

    def test_idle_is_not_transient(self):
        """IDLE reverting to itself would arm a pointless timer."""
        assert MascotState.IDLE not in TRANSIENT_STATES

    def test_busy_states_persist(self):
        """Work poses must not time out while the work is still running."""
        assert MascotState.THINKING not in TRANSIENT_STATES
        assert MascotState.WORKING not in TRANSIENT_STATES
        assert MascotState.EXPLAINING not in TRANSIENT_STATES

    def test_idle_cycle_is_populated(self):
        assert len(IDLE_CYCLE) >= 2
        assert all(isinstance(s, MascotState) for s in IDLE_CYCLE)
        assert MascotState.IDLE in IDLE_CYCLE

    def test_hold_is_positive(self):
        assert STATE_HOLD_MS > 0

    def test_filenames_are_unique(self):
        names = [s.filename for s in MascotState]
        assert len(names) == len(set(names))


class TestAssetPath:
    def test_resolves_independently_of_cwd(self, tmp_path, monkeypatch):
        """Regression: lookups used to be relative to the launch directory."""
        from_project = asset_path("mascot", "idle.png")
        monkeypatch.chdir(tmp_path)
        assert asset_path("mascot", "idle.png") == from_project
        assert os.path.exists(asset_path("mascot", "idle.png"))

    def test_path_is_absolute(self):
        assert os.path.isabs(asset_path("icons", "tray.png"))

    def test_uses_meipass_when_frozen(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        try:
            assert assets_root() == tmp_path / "assets"
        finally:
            monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    def test_missing_asset_reports_false(self):
        assert not asset_exists("mascot", "does_not_exist.png")


class TestGreetings:
    def test_all_message_keys_are_states(self):
        assert all(isinstance(s, MascotState) for s in GREETING_MESSAGES)

    def test_every_pose_has_at_least_one_line_where_defined(self):
        assert all(len(lines) > 0 for lines in GREETING_MESSAGES.values())

    def test_silent_state_returns_none(self):
        """READY has no lines mapped — reacting to it should stay silent, not crash."""
        assert greeting_for(MascotState.READY) is None

    def test_greeting_state_speaks(self):
        assert greeting_for(MascotState.GREETING) in GREETING_MESSAGES[MascotState.GREETING]

    def test_index_cycles_through_lines(self):
        lines = GREETING_MESSAGES[MascotState.GREETING]
        for i in range(len(lines) * 2):
            assert greeting_for(MascotState.GREETING, i) == lines[i % len(lines)]
