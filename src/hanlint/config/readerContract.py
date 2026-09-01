"""모델과 실행 환경에 독립적인 최소 Reader Contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .writingBrief import checkedString, checkedStrings

CONTRACT_VERSION = 1


@dataclass(frozen=True)
class Contract:
    """독자, 글의 목표, 선언한 사실만 담는 닫힌 입력 계약."""

    reader: str
    goal: str
    facts: tuple[str, ...]
    version: int = CONTRACT_VERSION

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
        return cls(
            reader=checkedString(data["reader"], "reader"),
            goal=checkedString(data["goal"], "goal"),
            facts=checkedStrings(data["facts"], "facts"),
            version=version,
        )

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


def loadContract(path: str | Path) -> Contract:
    """UTF-8 JSON 파일을 엄격한 Reader Contract로 읽는다."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"reader contract JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    return Contract.fromMapping(data)


__all__ = ["CONTRACT_VERSION", "Contract", "loadContract"]
