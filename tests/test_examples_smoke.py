"""Every directly executable example must remain importable and buildable."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


EXAMPLES = Path(__file__).parents[1] / "examples"
FACTORIES = (
    "make_view", "content", "main_view", "settings_view", "inspector_view",
    "adaptive_content",
)


@pytest.mark.parametrize(
    "path", [path for path in sorted(EXAMPLES.glob("*.py")) if path.name != "appkit_support.py"],
    ids=lambda path: path.name,
)
def test_example_imports_and_declared_view_factories_build(path, monkeypatch, tmp_path):
    monkeypatch.setenv("AUI_EXAMPLE_DATA_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(EXAMPLES))
    spec = importlib.util.spec_from_file_location(f"example_smoke_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in FACTORIES:
        factory = getattr(module, name, None)
        if not callable(factory):
            continue
        try:
            factory()
        except TypeError:
            # Geometry/scene callbacks legitimately require a framework value.
            continue
