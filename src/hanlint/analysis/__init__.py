"""분석 층. 문장 분리와 형태 판정을 분석기 인터페이스 뒤에 둔다.

`surface` 는 표준 라이브러리만 쓰는 기본이고 `kiwi` 는 `pip install hanlint[kiwi]` 가 있을 때 갈아 끼우는
정밀 모드다. 규칙은 이 인터페이스만 보고 분석기가 무엇인지 모른다. 왜 이렇게 나눴는지는
memory/architecture/analyzerChoice.md 와 PRD 3절이 설명한다.
"""

from __future__ import annotations

from .analyzer import Analyzer, Sentence
from .surface.surfaceAnalyzer import SurfaceAnalyzer

__all__ = ["Analyzer", "Sentence", "SurfaceAnalyzer", "makeAnalyzer"]


def makeAnalyzer(name: str = "surface") -> Analyzer:
    """이름으로 분석기를 만든다. kiwi 가 설치되지 않았으면 다음 행동을 담은 오류를 낸다."""
    if name == "surface":
        return SurfaceAnalyzer()
    if name == "kiwi":
        from .kiwi.kiwiAnalyzer import KiwiAnalyzer

        return KiwiAnalyzer()
    raise ValueError(f"모르는 분석기: {name}. surface 또는 kiwi 를 쓴다")
