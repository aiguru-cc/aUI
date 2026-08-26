"""Path bootstrap for aUI examples.

Adds the project ``src/`` directory to ``sys.path`` so examples can be run
directly with ``python3 examples/xxx.py`` from anywhere, without installing
the package or setting PYTHONPATH.

Import this first in every example::

    import _bootstrap  # noqa: F401
"""
import os
import sys

# examples/ -> project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)
