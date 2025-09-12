"""Flow modules for the ai-pipeline pipeline."""

from typing import Any, Callable

FLOWS: list[Callable[..., Any]] = []

__all__ = [
    "FLOWS",
]
