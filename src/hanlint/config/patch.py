"""이유가 붙은 정확 국소 Patch 입력 계약."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .writingBrief import checkedString


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


def loadPatch(path: str | Path) -> Patch:
    """UTF-8 JSON 파일을 엄격한 Patch로 읽는다."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"patch JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    return Patch.fromMapping(data)


__all__ = ["Patch", "loadPatch"]
