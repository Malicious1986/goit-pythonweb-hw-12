"""Compatibility package to satisfy pyproject package include.

This package exists so Poetry can find the `contacts` package under `src/`.
It re-exports the `api` module functions where appropriate if needed.
"""

# Minimal package marker to satisfy build tooling
__all__ = []
