"""지문 층. 글을 한 번 읽어 문장, 문단, 절, 글의 지문을 만든다.

규칙과 분석과 프로파일과 지도가 전부 이 위에서 일한다. 컴파일러의 중간 표현과 같다. 사전 매치까지 여기서
한 번 하므로 위층은 텍스트를 다시 읽지 않는다.
"""

from __future__ import annotations

from .build import buildFingerprint
from .documentPrint import DocumentPrint
from .paragraphPrint import ParagraphPrint
from .sectionPrint import SectionPrint
from .sentencePrint import DictionaryMatch, SentencePrint

__all__ = [
    "DictionaryMatch",
    "DocumentPrint",
    "ParagraphPrint",
    "SectionPrint",
    "SentencePrint",
    "buildFingerprint",
]
