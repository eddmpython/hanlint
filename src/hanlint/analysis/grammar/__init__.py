"""형태 층. 어절 판정과 무관하게 참인 한국어 형태 사실만 둔다.

조사 교체 (josa), 종결 활용 (ending), 사동과 피동 분해 (voice), 문체 판별과 변환 (register)이 있고
모두 `hangul`의 자모 산술 위에 선다. 뜻은 다루지 않는다. 기준 말뭉치 17,420문장에서 합니다체와
한다체 평서 종결형 14,247건을 재어 14,201건을 원문 글자대로 다시 만들었다 (2026-08-28).
"""

from __future__ import annotations

from .ending import (
    ADJECTIVE,
    COPULA,
    DECLARATIVE,
    HAEYO,
    HANDA,
    HAPNIDA,
    IMPERATIVE,
    PROPOSITIVE,
    REGISTERS,
    VERB,
    Predicate,
    conjugate,
    parsePredicate,
    render,
)
from .josa import fitJosa, josaSwap
from .register import MIXED, NONE, Conversion, convertRegister, convertTemplate, documentRegister, lastWord, registerOfWord
from .voice import CAUSATIVE, PASSIVE, VoiceForm, decomposeCausative, decomposePassive, decomposeVoice

__all__ = [
    "ADJECTIVE",
    "COPULA",
    "HAEYO",
    "HANDA",
    "HAPNIDA",
    "IMPERATIVE",
    "MIXED",
    "NONE",
    "REGISTERS",
    "Conversion",
    "DECLARATIVE",
    "Predicate",
    "PROPOSITIVE",
    "VoiceForm",
    "CAUSATIVE",
    "PASSIVE",
    "VERB",
    "conjugate",
    "convertRegister",
    "convertTemplate",
    "decomposeCausative",
    "decomposePassive",
    "decomposeVoice",
    "documentRegister",
    "fitJosa",
    "josaSwap",
    "lastWord",
    "parsePredicate",
    "registerOfWord",
    "render",
]
