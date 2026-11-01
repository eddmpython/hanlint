"""종결 어미의 공개 API.

구현은 기존 `predicate.py`에 있다. 이 모듈 이름은 형태 부분의 네 구성요소 가운데 ending을 공개하고,
`predicate.py`는 서술어 자료형과 활용 산술을 갖는 내부 구현으로 남긴다.
"""

from __future__ import annotations

from .predicate import (
    ADJECTIVE,
    COPULA,
    DECLARATIVE,
    HAEYO,
    HANDA,
    HAPNIDA,
    IMPERATIVE,
    KKA_QUESTION,
    PAST,
    PRESENT,
    PROPOSITIVE,
    QUESTION,
    REGISTERS,
    VERB,
    Predicate,
    conjugate,
    parsePredicate,
    render,
)

__all__ = [
    "ADJECTIVE",
    "COPULA",
    "DECLARATIVE",
    "HAEYO",
    "HANDA",
    "HAPNIDA",
    "IMPERATIVE",
    "KKA_QUESTION",
    "PAST",
    "PRESENT",
    "PROPOSITIVE",
    "QUESTION",
    "REGISTERS",
    "VERB",
    "Predicate",
    "conjugate",
    "parsePredicate",
    "render",
]
