from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import firstMatchFindings


@rule("screenSentence", mechanism="dictionary")
def screenSentence(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """낱말 자리에 놓인 문장. 진행, 실패, 요구, 완료를 종결어미로 쓴 화면의 글.

    왜: 화면의 글은 데이터의 이름과 사용자 동작의 낱말이다. 빈 상태는 `<대상> 없음`, 진행은 `<동작> 중`, 실패는
        `<대상> <동작> 실패`, 요구는 `<대상> 필요`, 끝난 일은 상태 한 낱말 (승인됨) 이다. 문장은 제목이 이미 말한 것을
        되풀이하거나 화면을 해설하고, 사용자는 낱말을 읽고 문장은 건너뛴다.
    어디서: 화면 낱말 규약 (운영 중인 세무 앱의 화면에서 실측, 2026-09-17, 운영자 지시).
    실측: 운영 화면 "요청을 완료하지 못했습니다", 설치 페이지
        "상태를 확인하지 못했습니다.", 온보딩 "대시보드를 열고 있습니다", 진단 "자료 갱신을 위한 로그인이 필요합니다".
        사전은 data/screenSentence.toml 이고 설정의 dictionary.screenSentence 로 더한다.
    고치기: 종결어미를 떼고 낱말로 만든다. 요청을 완료하지 못했습니다 는 요청 실패, 대시보드를 열고 있습니다 는
        대시보드 여는 중, 로그인이 필요합니다 는 로그인 필요, 변경을 완료했습니다 는 변경됨. 문장이 정말 필요한 글
        (장표, 고지, 실패 원인) 은 문장이 허용된 글 모듈로 옮기고 chat 프리셋으로 잰다.
    안 잡는 것: 종결어미가 없는 글. 프리셋 screen 에서만 켜진다. 산문 프리셋은 문장이 정상이라 끈다. 문장 하나에
        무늬가 여럿이면 가장 앞의 것 하나만 짚는다.
    """
    yield from firstMatchFindings(doc, "screenSentence", "screenSentence")
