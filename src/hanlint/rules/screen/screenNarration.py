from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import firstMatchFindings


@rule("screenNarration", mechanism="dictionary")
def screenNarration(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """화면이 자기를 해설하는 말. 빈 자리의 예고, 이 화면은, 잠시 뒤 다시, 할 수 있습니다.

    왜: 빈 상태에 "오면 여기에 표시됩니다" 를 두면 사용자는 없는 것을 읽는다. "이 화면은 비밀번호로 엽니다" 는 제목이
        이미 한 말이다. "잠시 뒤 다시 시도해 주세요" 는 실패를 감싸는 위로이고 다시 시도는 단추다. "볼 수 있습니다" 는
        단추와 칸이 이미 보이는 능력을 글로 되풀이한다. 넷 다 정보가 아니라 해설이다.
    어디서: 화면 낱말 규약 (운영 중인 세무 앱의 화면에서 실측, 2026-09-17, 운영자 지시).
    실측: 운영 화면 "계약 신청이 도착하면 여기에 표시됩니다",
        "내려받기 페이지에서 요청이 오면 여기에 표시됩니다", "이 화면은 비밀번호로 엽니다. 비밀번호는 이 탭에서만 기억합니다",
        수집 화면 "진행 상태를 갱신하지 못했습니다. 저장된 자료는 유지되며 잠시 뒤 다시 확인합니다".
        사전은 data/screenNarration.toml 이고 설정의 dictionary.screenNarration 으로 더한다.
    고치기: 빈 상태는 `<대상> 없음` (요청 없음, 계약 없음). 자기 설명과 능력 서술은 지운다. 재시도 서술은
        `<대상> <동작> 실패` 로 줄이고 다시 시도 단추를 둔다. 문장이 허용된 글에서도 같은 말은 사족이라
        enforceStyle 로 켜서 잰다.
    안 잡는 것: 사전에 없는 해설. "이 컴퓨터", "이 회사" 처럼 화면이 아닌 것을 가리키는 지시어. 프리셋 screen 밖에서는
        enforceStyle 에 넣어야 돈다.
    """
    yield from firstMatchFindings(doc, "screenNarration", "screenNarration")
