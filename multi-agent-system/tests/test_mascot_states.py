"""Tests for the mascot state table and asset lookup.

Imports only pure-Python modules — no PyQt6, so these run headless.
"""
import os
import sys

import pytest

from gui.assets import asset_exists, asset_path, assets_root
from gui.mascot_states import (
    IDLE_CYCLE,
    STATE_HOLD_MS,
    TOOL_STATES,
    TRANSIENT_STATES,
    MascotState,
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
