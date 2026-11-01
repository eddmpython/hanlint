from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import firstMatchFindings


@rule("screenSentence", mechanism="dictionary")
def screenSentence(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """단어를 써야 할 곳에 놓인 문장. 진행, 실패, 요구, 완료를 종결어미로 쓴 화면 글.

    왜: 화면 글은 데이터의 이름과 사용자가 하는 동작의 이름이다. 빈 상태는 `<대상> 없음`, 진행은 `<동작> 중`, 실패는
        `<대상> <동작> 실패`, 요구는 `<대상> 필요`, 끝난 일은 상태를 나타내는 단어 하나(`승인됨`)로 쓴다. 문장은
        제목이 이미 말한 것을 되풀이하거나 화면을 해설하고, 사용자는 단어만 읽고 문장은 건너뛴다.
    어디서: 실제 운영 중인 앱의 화면 글을 검토해 정한 규칙이다.
    실측: 운영 화면 "요청을 완료하지 못했습니다", 설치 페이지
        "상태를 확인하지 못했습니다.", 온보딩 "대시보드를 열고 있습니다", 진단 화면 "자료 갱신을 위한 로그인이 필요합니다".
        사전은 data/screenSentence.toml에 있고 설정 dictionary.screenSentence로 항목을 더한다.
    고치기: 종결어미를 떼고 단어로 만든다. `요청을 완료하지 못했습니다`는 `요청 실패`, `대시보드를 열고 있습니다`는
        `대시보드 여는 중`, `로그인이 필요합니다`는 `로그인 필요`, `변경을 완료했습니다`는 `변경됨`으로 쓴다. 문장이
        꼭 필요한 글(장표, 고지, 실패 원인)은 문장이 허용된 글 모듈로 옮기고 chat 프리셋으로 검사한다.
    안 잡는 것: 종결어미가 없는 글은 잡지 않는다. screen 프리셋에서만 켜지고, 산문 프리셋에서는 문장이 정상이라
        꺼진다. 문장 하나에 걸리는 형태가 여럿이면 가장 앞의 것 하나만 짚는다.
    """
    yield from firstMatchFindings(doc, "screenSentence", "screenSentence")
