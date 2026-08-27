"""구멍 종류. data/holeKinds.toml 을 읽어 규칙 이름을 색과 기호로 잇는다."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from ..data import loadToml


@dataclass(frozen=True)
class HoleKind:
    id: str
    name: str
    symbol: str
    ansi: int
    hex: str


UNKNOWN = HoleKind("unknown", "기타", "?", 250, "#BBBBBB")


@cache
def kindsByRule() -> dict[str, HoleKind]:
    mapping: dict[str, HoleKind] = {}
    for raw in loadToml("holeKinds.toml", "kind"):
        kind = HoleKind(raw["id"], raw["name"], raw["symbol"], int(raw["ansi"]), raw["hex"])
        for ruleName in raw["rules"]:
            mapping[ruleName] = kind
    return mapping


def kindOf(ruleName: str) -> HoleKind:
    return kindsByRule().get(ruleName, UNKNOWN)


@cache
def allKinds() -> tuple[HoleKind, ...]:
    seen: dict[str, HoleKind] = {}
    for kind in kindsByRule().values():
        seen.setdefault(kind.id, kind)
    return tuple(seen.values())
