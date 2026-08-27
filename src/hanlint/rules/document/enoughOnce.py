from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import matchedTexts
from ..finding import SENTENCE, Finding
from ..registry import rule


@rule("enoughOnce")
def enoughOnce(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """여기까지면 충분합니다 로 끊는 문장이 한 글에 두 번 이상 나오는 것.

    왜: 기본 사용법이 끝나는 지점을 한 번 끊어 주면 독자는 여기서 멈춰도 된다는 것을 안다. 그 문장이
        절마다 나오면 계속 끝나는 척하다 이어지는 꼴이 되고, 어디가 진짜 끝인지 알 수 없어 신호가 죽는다.
    어디서: cinch 의 전역 blog-writing 스킬, 절은 앞 절이 못 한 일에서 시작한다. `여기까지면 만들어 쓰는 데
        충분합니다. 아래부터는 ~할 때 봅니다.` 글 전체에 한 번만 쓴다. 절마다 넣으면 계속 끝나는 척하다
        이어지는 꼴이 된다. 표지 목록은 data/enoughMarkers.txt.
    고치기: 기본 사용법이 진짜로 끝나는 자리 하나만 남기고 나머지는 지운다. 지운 자리는 앞 절이 만든 것을
        이름으로 부르고 다음 행동을 붙이는 문장으로 잇는다.
    안 잡는 것: 한 번만 쓴 글. 인용 안의 같은 문장은 지문이 이미 인용으로 걸러 둔다.
    """
    found = [(s, matchedTexts(s.text, "enoughMarkers.txt")) for s in doc.sentences]
    breaks = [(s, texts[0]) for s, texts in found if texts]
    if len(breaks) < 2:
        return
    first = breaks[0][0]
    for sentence, text in breaks[1:]:
        yield Finding(
            "enoughOnce",
            sentence.line,
            sentence.text,
            f"`{text}` 로 끊는 문장이 {first.line}행에 이미 있다. 글 전체에 한 번만 쓴다. 계속 끝나는 척하다 이어지는 꼴이 된다",
            None,
            "error",
            SENTENCE,
            sentence.index,
        )
