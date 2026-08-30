"""배포한 종류별 수사 구조 백분위. 원문 문장과 제목은 싣지 않는다."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from functools import cache

from .load import loadJson

BLUEPRINT_VERSION = 1
FORBIDDEN_VALUE_KEYS = {"heading", "name", "sentence", "text", "title", "url"}
SHA256_VALUE = re.compile(r"[0-9a-f]{64}")
SOURCE_ID_VALUE = re.compile(r"[A-Za-z][A-Za-z0-9]*")


@dataclass(frozen=True)
class BlueprintReference:
    kind: str
    documents: int
    sourceIds: tuple[str, ...]
    metrics: dict[str, dict[str, int]]

    @classmethod
    def fromMapping(cls, kind: str, data: dict) -> BlueprintReference:
        """JSON 종류 하나를 숫자 구조 참조로 바꾼다."""
        return cls(
            kind=kind,
            documents=int(data["documents"]),
            sourceIds=tuple(data["sourceIds"]),
            metrics={name: {key: int(value) for key, value in values.items()} for name, values in data["metrics"].items()},
        )


def blueprintBoundaryViolations(data: object) -> tuple[str, ...]:
    """배포 청사진에 원문을 담을 수 있는 키나 허가되지 않은 문자열이 있는지 찾는다."""
    if not isinstance(data, dict):
        return ("root는 JSON 객체여야 한다",)
    types = data.get("types", {})
    if not isinstance(types, dict):
        return ("root.types는 JSON 객체여야 한다",)
    sourceIds: set[str] = set()
    violations: list[str] = []
    for kind, item in types.items():
        if not isinstance(item, dict) or not isinstance(item.get("sourceIds"), list):
            violations.append(f"root.types.{kind}.sourceIds는 배열이어야 한다")
            continue
        sourceIds.update(sourceId for sourceId in item["sourceIds"] if isinstance(sourceId, str))
    violations.extend(
        f"허가된 꼴이 아닌 sourceId다: {sourceId}" for sourceId in sorted(sourceIds) if not SOURCE_ID_VALUE.fullmatch(sourceId)
    )
    sourceIds = {sourceId for sourceId in sourceIds if SOURCE_ID_VALUE.fullmatch(sourceId)}

    def inspect(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in FORBIDDEN_VALUE_KEYS:
                    violations.append(f"{path}.{key}는 원문을 실을 수 있는 키다")
                inspect(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                inspect(item, f"{path}[{index}]")
        elif isinstance(value, str) and value not in sourceIds and not SHA256_VALUE.fullmatch(value):
            violations.append(f"{path}에 출처 ID나 SHA256이 아닌 문자열이 있다")

    inspect(data, "root")
    return tuple(violations)


@cache
def _loadBlueprints() -> tuple[dict, dict[str, BlueprintReference]]:
    data = loadJson("blueprints.json")
    violations = blueprintBoundaryViolations(data)
    if violations:
        raise ValueError("배포 수사 구조 청사진의 원문 경계가 깨졌다: " + "; ".join(violations))
    if data.get("version") != BLUEPRINT_VERSION or data.get("corpus", {}).get("containsSourceText") is not False:
        raise ValueError("배포 수사 구조 청사진의 version 또는 원문 경계가 다르다")
    references = {kind: BlueprintReference.fromMapping(kind, value) for kind, value in sorted(data["types"].items())}
    return data["corpus"], references


def shippedBlueprints() -> tuple[dict, dict[str, BlueprintReference]]:
    """호출자가 배포 정본 캐시를 바꾸지 못하도록 독립 복사본을 돌려준다."""
    return deepcopy(_loadBlueprints())


def referenceOf(kind: str) -> tuple[dict, BlueprintReference]:
    corpus, references = shippedBlueprints()
    if kind not in references:
        raise ValueError(f"수사 구조 청사진에 없는 글 종류다: {kind}")
    return corpus, references[kind]


__all__ = [
    "BLUEPRINT_VERSION",
    "BlueprintReference",
    "blueprintBoundaryViolations",
    "referenceOf",
    "shippedBlueprints",
]
