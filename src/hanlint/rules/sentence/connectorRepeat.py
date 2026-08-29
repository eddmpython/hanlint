from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule
from ..shared import runsOf


@rule("connectorRepeat", mechanism="repeat")
def connectorRepeat(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 접속부사로 시작하는 문장이 한 문단 안에 연달아 오는 자리.

    왜: 그리고, 그래서 를 연달아 붙이면 문장 사이의 관계가 전부 같은 것으로 읽히고 리듬이 죽는다.
    어디서: 글쓰기 스킬의 사실과 목소리 (같은 접속사를 연달아 쓰지 않는다). 이태준 문장강화, 유시민
        글쓰기 특강. 접속부사 목록은 data/connectors.txt. 셈은 반복 기제 (rules/shared/repeat.py) 의 runsOf 다.
    고치기: 앞 문장에서 만든 파일이나 값의 이름을 다시 불러 잇는다. 접속사는 그렇게 이어지지 않을 때만.
    안 잡는 것: 문단이 바뀌면 다시 센다. 다른 접속사가 이어지는 것은 잡지 않는다.
    """
    for paragraph in doc.paragraphs:
        sentences = paragraph.sentences
        # 열쇠는 문두 접속부사다. 접속부사가 없는 문장은 저마다 다른 열쇠를 받아 구간을 끊는다.
        keys = [sentence.connectorStart or f"__{sentence.index}" for sentence in sentences]
        for start, length, connector in runsOf(keys, 2):
            for sentence in sentences[start + 1 : start + length]:
                yield Finding(
                    "connectorRepeat",
                    sentence.line,
                    sentence.text,
                    f"`{connector}` 로 시작하는 문장이 연달아 온다. 앞에서 만든 것의 이름을 불러 잇는다",
                    None,
                    "error",
                    SENTENCE,
                    sentence.index,
                )
