"""The brain registry — a "brain" is a self-contained ``(seed, cooccurrence)`` pair (ADR 0044).

The engine, pipeline and every CLI command are already parameterised by a seed + co-occurrence path,
so serving *several* graphs the user can switch between needs no engine change — only a way to
enumerate the available brains. The **main** brain stays at ``data/seed.json`` (unmoved, so nothing
downstream breaks); additional brains live under ``data/brains/<name>/`` as ``seed.json`` +
``cooccurrence.json``, with an optional ``meta.json`` carrying a display ``label``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_DATA = Path("data")
_MAIN_LABEL = "Old World"


@dataclass(frozen=True)
class BrainSpec:
    """One selectable brain: a stable ``name``, a display ``label``, and its two data paths."""

    name: str
    label: str
    seed_path: Path
    cooccurrence_path: Path


def _titleize(name: str) -> str:
    """Fallback display label from a dir name (``twentieth_century`` → ``Twentieth Century``)."""
    return name.replace("_", " ").title()


def _label(directory: Path) -> str:
    """Read ``meta.json``'s ``label`` if present, else derive one from the directory name."""
    meta = directory / "meta.json"
    if meta.exists():
        try:
            value = json.loads(meta.read_text(encoding="utf-8")).get("label")
        except (json.JSONDecodeError, OSError):
            value = None
        if value:
            return str(value)
    return _titleize(directory.name)


def available_brains(data_dir: Path = _DEFAULT_DATA) -> list[BrainSpec]:
    """Every selectable brain, **main first**, then ``data/brains/*`` in sorted order.

    A brain directory without a ``seed.json`` is skipped. The main brain is always present (it is
    the curated graph the whole project is built around); the list therefore never comes back empty.
    """
    brains = [
        BrainSpec("main", _MAIN_LABEL, data_dir / "seed.json", data_dir / "cooccurrence.json")
    ]
    brains_dir = data_dir / "brains"
    if brains_dir.exists():
        for directory in sorted(p for p in brains_dir.iterdir() if p.is_dir()):
            seed = directory / "seed.json"
            if seed.exists():
                brains.append(
                    BrainSpec(
                        directory.name, _label(directory), seed, directory / "cooccurrence.json"
                    )
                )
    return brains
