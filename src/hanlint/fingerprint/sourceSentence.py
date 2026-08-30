"""평문 지문의 문장을 마크다운 표식을 보존한 원문 문장에 다시 맞춘다."""

from __future__ import annotations

from ..analysis import splitSentences
from ..document import plainText
from .documentPrint import DocumentPrint
from .sentencePrint import SentencePrint


def sourceSentenceTexts(doc: DocumentPrint) -> dict[int, str]:
    """문장 수와 평문이 모두 같은 블록만 맞춘다. 확실하지 않으면 그 블록 전체를 기권한다."""
    byBlock: dict[int, list[SentencePrint]] = {}
    for sentence in doc.sentences:
        byBlock.setdefault(sentence.blockIndex, []).append(sentence)
    blocks = {block.index: block for block in doc.blocks}
    found: dict[int, str] = {}
    for blockIndex, plainSentences in byBlock.items():
        rawSentences = splitSentences(blocks[blockIndex].text)
        if len(rawSentences) != len(plainSentences):
            continue
        pairs = list(zip(plainSentences, rawSentences, strict=True))
        if any(plainText(raw.text) != plain.text for plain, raw in pairs):
            continue
        found.update((plain.index, raw.text) for plain, raw in pairs)
    return found


def sourceSentenceText(doc: DocumentPrint, sentence: SentencePrint) -> str | None:
    """마크다운 원문 문장을 확실히 대응시킬 수 있을 때만 돌려준다."""
    return sourceSentenceTexts(doc).get(sentence.index)
