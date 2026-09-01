"""모델과 실행 환경에 독립적인 최소 Reader Contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .writingBrief import checkedString, checkedStrings

CONTRACT_VERSION = 1


@dataclass(frozen=True, init=False)
class Contract:
    """독자, 글의 목표, 선언한 사실만 담는 닫힌 입력 계약."""

    reader: str
    goal: str
    facts: tuple[str, ...]
    version: int = CONTRACT_VERSION

    def __init__(self, reader: str, goal: str, facts: list[str] | tuple[str, ...], version: int = CONTRACT_VERSION):
        if isinstance(version, bool) or not isinstance(version, int) or version != CONTRACT_VERSION:
            raise ValueError(f"reader contract version 은 {CONTRACT_VERSION}이다: {version}")
        if not isinstance(facts, (list, tuple)) or not facts:
            raise ValueError("facts 는 비지 않은 문자열 배열이다")
        checkedFacts = tuple(checkedString(item, f"facts {index}번째") for index, item in enumerate(facts, start=1))
        if len(set(checkedFacts)) != len(checkedFacts):
            raise ValueError("facts 에 같은 값이 두 번 있다")
        object.__setattr__(self, "reader", checkedString(reader, "reader"))
        object.__setattr__(self, "goal", checkedString(goal, "goal"))
        object.__setattr__(self, "facts", checkedFacts)
        object.__setattr__(self, "version", version)

    @classmethod
    def fromMapping(cls, data: object) -> Contract:
        if not isinstance(data, dict):
            raise ValueError("reader contract 는 JSON 객체다")
        expected = {"version", "reader", "goal", "facts"}
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown:
            raise ValueError(f"reader contract 의 모르는 키: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"reader contract 의 빠진 키: {', '.join(missing)}")
        version = data["version"]
        if isinstance(version, bool) or not isinstance(version, int) or version != CONTRACT_VERSION:
            raise ValueError(f"reader contract version 은 {CONTRACT_VERSION}이다: {version}")
        return cls(data["reader"], data["goal"], checkedStrings(data["facts"], "facts"), version)

    @property
    def text(self) -> str:
        """보호 원자를 컴파일할 유일한 계약 본문."""
        return "\n".join((self.reader, self.goal, *self.facts))

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.asDict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode()).hexdigest()

    def asDict(self) -> dict:
        return {
            "version": self.version,
            "reader": self.reader,
            "goal": self.goal,
            "facts": list(self.facts),
        }


@dataclass(frozen=True)
class Patch:
    """기존 위반 하나에 이유를 연결한 정확 국소 치환."""

    reason: str
    before: str
    after: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", checkedString(self.reason, "reason"))
        object.__setattr__(self, "before", checkedString(self.before, "before"))
        object.__setattr__(self, "after", checkedString(self.after, "after"))
        if self.before == self.after:
            raise ValueError("patch before 와 after 는 달라야 한다")

    @classmethod
    def fromMapping(cls, data: object) -> Patch:
        if not isinstance(data, dict):
            raise ValueError("patch 는 JSON 객체다")
        expected = {"reason", "before", "after"}
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown:
            raise ValueError(f"patch 의 모르는 키: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"patch 의 빠진 키: {', '.join(missing)}")
        return cls(data["reason"], data["before"], data["after"])

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.asDict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode()).hexdigest()

    def asDict(self) -> dict:
        return {"reason": self.reason, "before": self.before, "after": self.after}


def loadContract(path: str | Path) -> Contract:
    """UTF-8 JSON 파일을 엄격한 Reader Contract로 읽는다."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"reader contract JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    return Contract.fromMapping(data)


def loadPatch(path: str | Path) -> Patch:
    """UTF-8 JSON 파일을 엄격한 Patch로 읽는다."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"patch JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    return Patch.fromMapping(data)


__all__ = ["CONTRACT_VERSION", "Contract", "Patch", "loadContract", "loadPatch"]
