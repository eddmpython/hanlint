"""지시어 규칙 둘이 함께 쓰는 같은 문장 안의 선행어 판정."""

from __future__ import annotations

from ...fingerprint import SentencePrint
from ...fingerprint.topics import overlap, topicsOf


def hasLocalAntecedent(sentence: SentencePrint) -> bool:
    """지시어보다 앞선 같은 문장 절에 이름이 있으면 되돌아갈 필요가 없다."""
    marker = sentence.deixis[0]
    start = sentence.text.find(marker)
    before = topicsOf(sentence.text[:start]) if start > 0 else frozenset()
    if marker.startswith("이것"):
        return bool(before)
    if marker.startswith("해당 "):
        return overlap(before, topicsOf(marker)) > 0.0
    return False
