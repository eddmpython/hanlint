from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, Finding
from ..registry import rule
from ..shared import overridingFindings


@rule("screenWord", mechanism="dictionary")
def screenWord(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """화면의 낱말. 개발 어휘 (메타데이터, 컴포넌트, 트랜잭션) 와 프로젝트가 한 이름으로 정한 낱말의 다른 이름.

    왜: 화면의 글은 데이터의 이름과 사용자 동작의 낱말이다. 용어에 설명이 필요한지는 독자와 문맥에 달려 있다.
        프로젝트가 같은 대상을 두 이름으로 부르면 사용자는 둘이 다른 것인지 묻는다. 프로젝트에서 한 이름으로
        정한 규약은 사전으로 확인하고, 일반 기술 용어의 뜻은 이름을 바꾸지 않고 설명한다.
    어디서: 화면 낱말 규약 (운영 중인 세무 앱의 화면에서 실측, 2026-09-17, 운영자 지시).
    실측: 화면 글 4,177개의 검토에서 용어 불일치 224건과
        개발 어휘 77건이 났고 산문 규칙은 하나도 짚지 못했다. 설명이 필요한지 검토할 기본 용어는
        data/screenWord.toml 이고 프로젝트의 정본 낱말은 설정의 dictionary.screenWord 로 더한다. 같은 자리에 기본 항목과
        설정 항목이 함께 걸리면 설정 항목이 이긴다.
    고치기: 기본 사전은 notice로 용어 설명이 필요한지 검토만 요청하며 치환을 제안하지 않는다. 기술 용어를
        설명하는 화면에서는 이름을 유지하고 정의와 예시를 붙인다. 프로젝트가 직접 정한 dictionary.screenWord의
        용어 규약만 error와 fix를 낸다. 2026-10-02 강의장 검토에서 쿼리 → 조회와 원자적 → 한 번에처럼
        뜻이 달라지는 기본 치환이 재현됐다. 낯선 용어라는 이유로 다른 명사를 만들지 않는다.
    안 잡는 것: 사전에 없는 말. 다른 낱말의 일부 (온라인의 라인, 파이프라인). 백틱과 따옴표 안의 인용. 프리셋
        screen 밖에서는 enforceStyle 에 넣어야 돈다.
    """
    yield from overridingFindings(doc, "screenWord", "screenWord", builtinSeverity=NOTICE)
