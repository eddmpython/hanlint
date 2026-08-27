from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, PARAGRAPH, Finding
from ..registry import rule


@rule("topicBreak")
def topicBreak(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 절 안에서 앞 문단과 화제어가 하나도 겹치지 않는 문단.

    왜: 앞 문단과의 관계를 새 문단 첫 문장에 드러내라는 규칙의 기계 판이다. 화제어가 전혀 안 겹치면 독자는
        어디로 넘어왔는지 모른다.
    어디서: 글쓰기 스킬의 사실과 목소리. TextTiling (Hearst 1997) 의 인접 블록 어휘 중첩을 임베딩 없이
        자카드로 잰다. 지문 계층이 가능하게 한 규칙이다. 최소 문장 수는 config.topicBreakMinSentences.
    고치기: 앞 문단에서 만든 파일이나 값의 이름을 새 문단 첫 문장에서 다시 부른다.
    안 잡는 것: 절이 바뀌는 자리 (절 경계는 화제가 바뀌는 것이 정상). 한 문장짜리 문단 (중첩이 원래 작다).
        화제어 근사가 거칠어 notice 로만 낸다.
    """
    for section in doc.sections:
        paragraphs = section.paragraphs
        for previous, paragraph in zip(paragraphs, paragraphs[1:], strict=False):
            if paragraph.overlapWithPrevious != 0.0:
                continue
            if min(previous.sentenceCount, paragraph.sentenceCount) < config.topicBreakMinSentences:
                continue
            yield Finding(
                "topicBreak",
                paragraph.startLine,
                paragraph.sentences[0].text,
                "앞 문단과 화제어가 하나도 겹치지 않는다. 앞에서 만든 것의 이름을 첫 문장에서 다시 부른다",
                None,
                NOTICE,
                PARAGRAPH,
                paragraph.index,
            )
