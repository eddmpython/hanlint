from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, Finding
from ..registry import rule
from ..shared import overridingFindings


@rule("screenWord", mechanism="dictionary")
def screenWord(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """화면의 단어. 개발 용어(메타데이터, 컴포넌트, 트랜잭션)와, 프로젝트가 한 이름으로 정한 단어를 다른 이름으로 쓴 곳.

    왜: 화면 글은 데이터의 이름과 사용자가 하는 동작의 이름이다. 용어에 설명이 필요한지는 독자와 문맥에 달려 있다.
        프로젝트가 같은 대상을 두 이름으로 부르면 사용자는 둘이 다른 것인지 묻는다. 프로젝트에서 한 이름으로 정한
        규약은 사전으로 확인하고, 일반 기술 용어는 이름을 바꾸지 않고 뜻을 설명한다.
    어디서: 실제 운영 중인 앱의 화면 글을 검토해 정한 규칙이다.
    실측: 화면 글 4,177개를 검토해 용어 불일치 224건과
        개발 용어 77건을 찾았는데 산문 규칙은 하나도 짚지 못했다. 설명이 필요한지 검토할 기본 용어는
        data/screenWord.toml에 있고, 프로젝트가 정한 단어는 설정 dictionary.screenWord로 더한다. 같은 곳에 기본 항목과
        설정 항목이 함께 걸리면 설정 항목을 따른다.
    고치기: 기본 사전은 용어 설명이 필요한지 검토해 달라는 확인 권고만 내고 바꿀 말을 제안하지 않는다. 기술 용어를
        설명하는 화면에서는 이름을 그대로 두고 정의와 예시를 붙인다. 프로젝트가 직접 정한 dictionary.screenWord의
        용어 규약만 오류와 고친 글을 낸다. 강의 자료를 검토할 때 `쿼리`를 `조회`로, `원자적`을 `한 번에`로 바꾸는
        기본 사전 항목이 뜻을 바꾼 일이 있었다. 낯선 용어라는 이유로 다른 명사를 만들지 않는다.
    안 잡는 것: 사전에 없는 말, 다른 단어 안에 든 말(`온라인`에 든 `라인`, `파이프라인`), 백틱과 따옴표로 감싼 인용은
        잡지 않는다. screen 프리셋이 아니면 enforceStyle에 넣어야 돈다.
    """
    yield from overridingFindings(doc, "screenWord", "screenWord", builtinSeverity=NOTICE)
