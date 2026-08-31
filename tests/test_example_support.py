"""Launcher contracts shared by directly executable AppKit examples."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from aui import Text, WindowGroup


def _support_module():
    path = Path(__file__).parents[1] / "examples" / "appkit_support.py"
    spec = importlib.util.spec_from_file_location("example_appkit_support", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_launcher_prefers_native_appkit(monkeypatch):
    support = _support_module()
    launches = []
    monkeypatch.setattr(support, "appkit_available", lambda: True)
    monkeypatch.setattr(support, "AppKitApplication", lambda scene: type(
        "Application", (), {"run": lambda self: launches.append(scene)}
    )())
    monkeypatch.setattr(support.sys, "argv", ["example.py"])

    support.run_window("Example", lambda: Text("Ready"), width=480, height=300)

    assert len(launches) == 1
    assert launches[0].title == "Example"
    assert launches[0].default_size.width == 480


def test_example_launcher_uses_standard_when_requested(monkeypatch):
    support = _support_module()
    launches = []
    monkeypatch.setattr(support, "appkit_available", lambda: True)
    monkeypatch.setattr(support.StandardBackend, "available", staticmethod(lambda: True))
    monkeypatch.setattr(support, "StandardApplication", lambda scene: type(
        "Application", (), {"run": lambda self: launches.append(scene)}
    )())
    monkeypatch.setattr(support.sys, "argv", ["example.py", "--standard"])

    support.run_window("Portable", Text("Ready"))

    assert len(launches) == 1
    assert launches[0].title == "Portable"


def test_example_scene_launcher_preserves_multi_window_scene(monkeypatch):
    support = _support_module()
    launches = []
    scenes = WindowGroup([])
    monkeypatch.setattr(support, "appkit_available", lambda: True)
    monkeypatch.setattr(support, "AppKitApplication", lambda scene: type(
        "Application", (), {"run": lambda self: launches.append(scene)}
    )())
    monkeypatch.setattr(support.sys, "argv", ["example.py"])

    support.run_scenes(scenes)

    assert launches == [scenes]
