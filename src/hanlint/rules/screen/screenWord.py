from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import overridingFindings


@rule("screenWord", mechanism="dictionary")
def screenWord(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """화면의 낱말. 개발 어휘 (메타데이터, 컴포넌트, 트랜잭션) 와 프로젝트가 한 이름으로 정한 낱말의 다른 이름.

    왜: 화면의 글은 데이터의 이름과 사용자 동작의 낱말이다. 개발자의 말 (컴포넌트, 메타데이터) 은 사용자가 모르는
        이름이고, 같은 것을 두 이름 (데이터와 자료, 회사와 수임처) 으로 부르면 사용자는 둘이 다른 것인지 묻는다.
        낱말 하나가 정해지면 그 뒤로는 사람의 기억이 아니라 사전이 지킨다.
    어디서: 화면 낱말 규약 (운영 중인 세무 앱의 화면에서 실측, 2026-09-17, 운영자 지시).
    실측: 화면 글 4,177개의 검토에서 용어 불일치 224건과
        개발 어휘 77건이 났고 산문 규칙은 하나도 짚지 못했다. 사전은 data/screenWord.toml (어느 제품에서나 개발
        어휘인 말) 이고 프로젝트의 정본 낱말은 설정의 dictionary.screenWord 로 더한다. 같은 자리에 기본 항목과
        설정 항목이 함께 걸리면 설정 항목이 이긴다.
    고치기: fix 가 있는 항목은 그 낱말로 바꾼다 (`hanlint sheet` 가 고침 칸에 미리 적는다). fix 가 없는 항목은
        자리마다 사용자의 낱말을 고른다 (메타데이터 → 계약 정보, 감사 기록).
    안 잡는 것: 사전에 없는 말. 다른 낱말의 일부 (온라인의 라인, 파이프라인). 백틱과 따옴표 안의 인용. 프리셋
        screen 밖에서는 enforceStyle 에 넣어야 돈다.
    """
    yield from overridingFindings(doc, "screenWord", "screenWord")
