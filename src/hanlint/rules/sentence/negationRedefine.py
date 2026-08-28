from __future__ import annotations

import re
from collections.abc import Iterator

from ...analysis.grammar import COPULA as COPULA_KIND
from ...analysis.grammar import lastWord, parsePredicate
from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule

NEGATION = re.compile(r"단순(?:한|히)\s?.{0,15}?(?:이|가)\s?아(?:닙니다|니다|니에요|니죠|닌)")
COPULA = re.compile(r"(입니다|이다|이에요|예요)[.!]?$")


def isDefinition(text: str) -> bool:
    if COPULA.search(text.strip()):
        return True
    predicate = parsePredicate(lastWord(text))
    return predicate is not None and predicate.kind == COPULA_KIND


@rule("negationRedefine")
def negationRedefine(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """단순한 X 가 아닙니다 뒤에 Y 입니다 로 다시 정의하는 두 문장 공식.

    왜: 부정하고 재정의하는 대구는 AI 가 즐겨 쓰는 수사다. 독자는 X 가 아니라는 말에서 정보를 얻지 못하고
        Y 만 읽으면 된다.
    어디서: AI 문체 신호 조사 (gist 패턴7 부정 후 재정의, im-not-ai C-8 대칭 대구).
    고치기: 앞 문장을 지우고 Y 를 바로 쓴다. 필요하면 Y 가 무엇을 하는지 한 문장을 더한다.
    안 잡는 것: 뒤 문장이 정의문이 아닌 경우. 단순한 도구가 아닙니다. 그래서 설치가 어렵습니다 는 잡지
        않는다.
    """
    for paragraph in doc.paragraphs:
        sentences = paragraph.sentences
        for current, following in zip(sentences, sentences[1:], strict=False):
            if NEGATION.search(current.text) and isDefinition(following.text):
                yield Finding(
                    "negationRedefine",
                    current.line,
                    current.text,
                    "단순한 X 가 아닙니다 뒤에 Y 입니다 로 재정의하는 공식이다. 앞 문장을 지우고 Y 를 바로 쓴다",
                    None,
                    "error",
                    SENTENCE,
                    current.index,
                )
