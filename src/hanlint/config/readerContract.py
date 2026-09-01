"""모델과 실행 환경에 독립적인 최소 Reader Contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .writingBrief import checkedString, checkedStrings

CONTRACT_VERSION = 1
LATEST_CONTRACT_VERSION = 2
CONTRACT_VERSIONS = (CONTRACT_VERSION, LATEST_CONTRACT_VERSION)


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


@dataclass(frozen=True, init=False)
class ProtectedSurface:
    """사실의 뜻과 분리해 자동으로 잠근 숫자, URL, 코드와 링크."""

    numbers: tuple[str, ...]
    urls: tuple[str, ...]
    code: tuple[str, ...]
    links: tuple[str, ...]

    def __init__(
        self,
        numbers: list[str] | tuple[str, ...] = (),
        urls: list[str] | tuple[str, ...] = (),
        code: list[str] | tuple[str, ...] = (),
        links: list[str] | tuple[str, ...] = (),
    ):
        values = {"numbers": numbers, "urls": urls, "code": code, "links": links}
        for name, items in values.items():
            if isinstance(items, tuple):
                items = list(items)
            checked = checkedStrings(items, f"surface.{name}", allowEmpty=True)
            object.__setattr__(self, name, tuple(sorted(checked)))

    @classmethod
    def fromMapping(cls, data: object) -> ProtectedSurface:
        if not isinstance(data, dict):
            raise ValueError("surface 는 JSON 객체다")
        expected = {"numbers", "urls", "code", "links"}
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown:
            raise ValueError(f"surface 의 모르는 키: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"surface 의 빠진 키: {', '.join(missing)}")
        return cls(data["numbers"], data["urls"], data["code"], data["links"])

    @property
    def text(self) -> str:
        """기존 표면 비교기가 읽는 손실 없는 최소 표현."""
        values = [*self.numbers, *self.urls]
        values.extend(f"`{value}`" for value in self.code)
        values.extend(f"[]({value})" for value in self.links)
        return "\n".join(values)

    def asDict(self) -> dict:
        return {
            "numbers": list(self.numbers),
            "urls": list(self.urls),
            "code": list(self.code),
            "links": list(self.links),
        }


@dataclass(frozen=True, init=False)
class Outline:
    """한 수준의 마크다운 제목 순서를 정확히 잠근 글 구조."""

    level: int
    headings: tuple[str, ...]

    def __init__(self, level: int, headings: list[str] | tuple[str, ...]):
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 6:
            raise ValueError(f"outline.level 은 1~6 정수다: {level}")
        if isinstance(headings, tuple):
            headings = list(headings)
        object.__setattr__(self, "level", level)
        object.__setattr__(self, "headings", checkedStrings(headings, "outline.headings"))

    @classmethod
    def fromMapping(cls, data: object) -> Outline:
        if not isinstance(data, dict):
            raise ValueError("outline 은 JSON 객체다")
        expected = {"level", "headings"}
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown:
            raise ValueError(f"outline 의 모르는 키: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"outline 의 빠진 키: {', '.join(missing)}")
        return cls(data["level"], data["headings"])

    def asDict(self) -> dict:
        return {"level": self.level, "headings": list(self.headings)}


@dataclass(frozen=True, init=False)
class ContractV2:
    """사람이 승인한 사실, 자동 표면과 글 구조를 분리한 Reader Contract."""

    reader: str
    goal: str
    facts: tuple[str, ...]
    surface: ProtectedSurface
    outline: Outline
    version: int = LATEST_CONTRACT_VERSION

    def __init__(
        self,
        reader: str,
        goal: str,
        facts: list[str] | tuple[str, ...],
        surface: ProtectedSurface | dict,
        outline: Outline | dict,
        version: int = LATEST_CONTRACT_VERSION,
    ):
        if isinstance(version, bool) or not isinstance(version, int) or version != LATEST_CONTRACT_VERSION:
            raise ValueError(f"reader contract version 은 {LATEST_CONTRACT_VERSION}다: {version}")
        if isinstance(facts, tuple):
            facts = list(facts)
        object.__setattr__(self, "reader", checkedString(reader, "reader"))
        object.__setattr__(self, "goal", checkedString(goal, "goal"))
        object.__setattr__(self, "facts", checkedStrings(facts, "facts", allowEmpty=True))
        object.__setattr__(
            self,
            "surface",
            surface if isinstance(surface, ProtectedSurface) else ProtectedSurface.fromMapping(surface),
        )
        object.__setattr__(self, "outline", outline if isinstance(outline, Outline) else Outline.fromMapping(outline))
        object.__setattr__(self, "version", version)

    @classmethod
    def fromMapping(cls, data: object) -> ContractV2:
        if not isinstance(data, dict):
            raise ValueError("reader contract 는 JSON 객체다")
        expected = {"version", "reader", "goal", "facts", "surface", "outline"}
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown:
            raise ValueError(f"reader contract 의 모르는 키: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"reader contract 의 빠진 키: {', '.join(missing)}")
        return cls(data["reader"], data["goal"], data["facts"], data["surface"], data["outline"], data["version"])

    @property
    def text(self) -> str:
        """사람이 쓴 계약과 자동 표면을 기존 원자 비교기에 주는 본문."""
        return "\n".join(value for value in (self.reader, self.goal, *self.facts, self.surface.text) if value)

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
            "surface": self.surface.asDict(),
            "outline": self.outline.asDict(),
        }


def parseContract(data: object) -> Contract | ContractV2:
    """version 필드로 닫힌 Reader Contract 구현을 고른다."""
    if not isinstance(data, dict):
        raise ValueError("reader contract 는 JSON 객체다")
    version = data.get("version")
    if version == CONTRACT_VERSION:
        return Contract.fromMapping(data)
    if version == LATEST_CONTRACT_VERSION:
        return ContractV2.fromMapping(data)
    raise ValueError(f"reader contract version 은 {CONTRACT_VERSIONS} 가운데 하나다: {version}")


def loadContract(path: str | Path) -> Contract | ContractV2:
    """UTF-8 JSON 파일을 엄격한 Reader Contract로 읽는다."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"reader contract JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    return parseContract(data)


__all__ = [
    "CONTRACT_VERSION",
    "CONTRACT_VERSIONS",
    "LATEST_CONTRACT_VERSION",
    "Contract",
    "ContractV2",
    "Outline",
    "ProtectedSurface",
    "loadContract",
    "parseContract",
]
