"""baseline 부분. 이미 있는 지적을 기준 파일에 적어 두고 새로 생긴 지적만 막는다. 내용은 store.py에 있다."""

from __future__ import annotations

from .store import DEFAULT_NAME, Baseline, build, keyOf, load, normalizeQuote, parse, pathKey, prune, render

__all__ = [
    "DEFAULT_NAME",
    "Baseline",
    "build",
    "keyOf",
    "load",
    "normalizeQuote",
    "parse",
    "pathKey",
    "prune",
    "render",
]
