"""글 분석(fingerprint) 부분. 글을 한 번 읽어 문장, 문단, 절, 글마다 잰 값(분석 결과)을 만든다.

규칙과 분석과 프로파일과 지도가 모두 이 결과를 읽는다. 컴파일러의 중간 표현과 같다. 사전 매치까지 여기서
한 번 하므로 다음 단계는 텍스트를 다시 읽지 않는다.
"""

from __future__ import annotations

from .build import buildFingerprint
from .codeBlocks import CodeBlock, codeBlocksOf
from .documentPrint import DocumentPrint
from .paragraphPrint import ParagraphPrint
from .readerState import ReaderState, ReaderTrail, readerKind
from .sectionPrint import SectionPrint
from .sentencePrint import DictionaryMatch, SentencePrint
from .sourceSentence import sourceSentenceText, sourceSentenceTexts

__all__ = [
    "CodeBlock",
    "DictionaryMatch",
    "DocumentPrint",
    "ParagraphPrint",
    "ReaderState",
    "ReaderTrail",
    "SectionPrint",
    "SentencePrint",
    "sourceSentenceText",
    "sourceSentenceTexts",
    "buildFingerprint",
    "codeBlocksOf",
    "readerKind",
]
