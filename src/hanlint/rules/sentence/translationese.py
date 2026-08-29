from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("translationese", mechanism="dictionary")
def translationese(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """~에 있어서, ~에 의해, ~을 통해, ~로부터, ~에도 불구하고 같은 번역투.

    왜: 영어와 일본어 구문을 그대로 옮긴 꼴이라 한국어로 읽을 때 한 박자 늦다. 독자가 머릿속에서
        다시 번역한다.
    어디서: 국립국어원 새국어생활 1990 과 2012, urimal.org 김민지 2020, egowriting 번역투 고치기,
        kubernetes.io 한국어 현지화 가이드. 사전은 data/translationese.toml.
    고치기: 항목마다 고친 예가 있다. 에 있어서 는 에서, 로부터 는 에게, 음에도 불구하고 는 지만.
        기계가 바꿀 수 있는 것은 fix 로 준다.
    안 잡는 것: 사전에 없는 번역투. 무생물 주어 타동사 구문처럼 구문 분석이 필요한 것은 잡지 않는다.
    """
    yield from dictionaryFindings(doc, "translationese", "translationese")
