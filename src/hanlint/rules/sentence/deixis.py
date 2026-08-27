from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.topics import overlap
from ..finding import SENTENCE, Finding
from ..registry import rule


@rule("deixis")
def deixis(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """이것, 해당 값, 위의 코드, 이러한 같은 지시어. 앞 문장에 가리킬 것이 있는 경우.

    왜: 독자가 스크롤을 되돌려 무엇을 가리키는지 찾아야 한다. 되돌리는 자리는 전부 이탈 지점이다.
    어디서: 글쓰기 스킬의 설명을 풀어 쓰기. 목록은 data/deixis.txt.
    고치기: 가리키는 파일, 값, 코드의 이름을 쓴다. 이것으로 파일이 만들어집니다 는 save 로 link.png 가
        만들어집니다 로.
    안 잡는 것: 앞 문장과 화제어가 하나도 겹치지 않는 지시어. 그것은 danglingDeixis 가 따로 짚는다.
        앞서 말한 X 처럼 이름을 다시 부르는 회수 표지.
    """
    for sentence in doc.sentences:
        if not sentence.deixis or sentence.index == 0:
            continue
        previous = doc.sentences[sentence.index - 1]
        if overlap(previous.topics, sentence.topics) == 0.0:
            continue
        yield Finding(
            "deixis",
            sentence.line,
            sentence.text,
            f"`{sentence.deixis[0]}` 은 독자가 스크롤을 되돌려야 하는 지시어다. 가리키는 파일, 값, 코드의 이름을 쓴다",
            None,
            "error",
            SENTENCE,
            sentence.index,
        )
