from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...document.model import CODE, EMBED, IMAGE, TABLE
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SECTION, Finding
from ..registry import rule

RESULT_KINDS = (CODE, EMBED, IMAGE, TABLE)
FILE_NAME = re.compile(r"[\w가-힣-]+\.(?:csv|xlsx|xls|parquet|json|png|jpg|svg|db|sqlite|txt|py|pdf|html|md)\b")
OUTPUT_WORDS = ("출력", "화면에", "찍힙니다", "나옵니다", "뜹니다", "보입니다", "만들어집니다", "생깁니다", "저장됩니다")


def leavesResult(section, doc: DocumentPrint) -> bool:
    if any(kind in RESULT_KINDS for kind in section.blockKinds):
        return True
    for paragraph in section.paragraphs:
        for sentence in paragraph.sentences:
            if FILE_NAME.search(sentence.text) or any(word in sentence.text for word in OUTPUT_WORDS):
                return True
    return False


@rule("sectionResult")
def sectionResult(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """산문만 있고 눈으로 볼 결과 (코드, 표, 그림, 끼워 넣은 영상이나 실행 칸, 파일 이름, 출력 문장) 가 없는 본문 절.

    왜: 따라 하는 독자는 한 절을 다 읽으면 자기 화면에서 확인할 것 하나를 기대한다. 확인할 것이 없는 절은
        과정이 아니라 참고 자료다. 글쓰기 스킬의 한 절을 다 읽으면 결과 하나가 남는다.
    어디서: 글쓰기 스킬의 절은 앞 절이 못 한 일에서 시작한다. sectionShapeMinParagraphs 문단을 넘는 절만 본다
        (설치, 계정 만들기 같은 짧은 구간은 뺀다).
    고치기: 그 절에서 독자가 만들거나 확인할 것을 하나 넣는다. 파일 하나, 화면 한 줄이면 된다.
    안 잡는 것: 도입과 마지막 절 (결말은 확인으로 닫는다). 짧은 절. 코드나 표나 그림이 있는 절. 링크 하나뿐인
        문단이나 주소만 있는 문단 (영상 카드, 실행 칸) 이 있는 절 (실측: eddmpython-course 01 의 한글 문서 절은 영상이
        셋인데 결과 없는 절로 잡혔다). 파일 이름이나 출력을 말하는 문장이 있는 절. 참고 문서라 결과가 원래 없으면 이
        규칙을 끈다. notice 로만 낸다.
    """
    body = doc.bodySections
    for index, section in enumerate(body):
        if index == len(body) - 1:
            continue
        if len(section.paragraphs) <= config.sectionResultMinParagraphs:
            continue
        if leavesResult(section, doc):
            continue
        yield Finding(
            "sectionResult",
            section.startLine,
            section.title,
            "이 절에 독자가 확인할 결과 (코드, 표, 그림, 파일, 출력) 가 없다. 만들거나 확인할 것을 하나 넣는다",
            None,
            NOTICE,
            SECTION,
            section.index,
        )
