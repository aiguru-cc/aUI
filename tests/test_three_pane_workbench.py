"""Contract checks for the persistent, cross-backend workbench example."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from aui import AppBar, IconButton, ResponsiveRow
from aui.core.commands import ToolbarModifier
from aui.core.presentation import SnackBarModifier


def _workbench_module():
    path = Path(__file__).parents[1] / "examples" / "three_pane_workbench.py"
    spec = importlib.util.spec_from_file_location("three_pane_workbench_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workbench_exposes_persistent_toolbar_responsive_and_feedback_ui():
    workbench = _workbench_module()
    view = workbench.make_view()
    views = view.flatten()
    gallery_views = workbench.visual_gallery().flatten()

    assert any(isinstance(item, AppBar) for item in views)
    assert any(isinstance(item, ResponsiveRow) for item in gallery_views)
    assert sum(isinstance(item, IconButton) for item in views) >= 2
    assert any(isinstance(item._modifier, SnackBarModifier) for item in views
               if hasattr(item, "_modifier"))
    assert any(isinstance(item._modifier, ToolbarModifier) for item in views
               if hasattr(item, "_modifier"))


def test_workbench_automation_and_reset_keep_feedback_state_consistent():
    workbench = _workbench_module()
    workbench.run_automation()
    assert workbench.show_snackbar.wrapped_value is True
    assert any("Automation completed" in event for event in workbench.activity.wrapped_value)

    workbench.reset_session()
    assert workbench.show_snackbar.wrapped_value is False
