from __future__ import annotations

from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.topics import overlap
from ..finding import SENTENCE, Finding
from ..registry import rule
from ..shared import hasLocalAntecedent


@rule("deixis", mechanism="reader")
def deixis(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """`이것`, `해당 값`, `위의 코드`, `이러한` 같은 지시어. 앞 문장에 가리킬 것이 있는 경우.

    왜: 독자가 스크롤을 되돌려 무엇을 가리키는지 찾아야 한다. 되돌아가야 하는 곳마다 독자가 글을 떠날 수 있다.
    어디서: 설명을 풀어 쓴다는 글쓰기 원칙. 지시어 목록은 data/deixis.txt에 있다. 독자가 바로 앞에서 읽은
        화제어와 이 문장의 화제어가 겹치면 여기서 짚는다.
    고치기: 가리키는 파일, 값, 코드의 이름을 쓴다. `이것으로 파일이 만들어집니다`는 `save로 link.png가
        만들어집니다`로 바꾼다.
    안 잡는 것: 앞 문장과 화제어가 하나도 겹치지 않는 지시어. 그것은 danglingDeixis가 따로 짚는다.
        `앞서 말한 X`처럼 이름을 다시 부르는 말.
    """
    for sentence in doc.sentences:
        if not sentence.deixis or sentence.index == 0:
            continue
        if hasLocalAntecedent(sentence):
            continue
        reader = doc.reader.beforeSentence[sentence.index]
        if overlap(reader.recent, sentence.topics) == 0.0:
            continue
        yield Finding(
            "deixis",
            sentence.line,
            sentence.text,
            f"`{sentence.deixis[0]}`{fitJosa(sentence.deixis[0], '은')} 독자가 스크롤을 되돌려야 하는 지시어다. "
            "가리키는 파일, 값, 코드의 이름을 쓴다",
            None,
            "error",
            SENTENCE,
            sentence.index,
        )
