from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import firstMatchFindings


@rule("screenTone", mechanism="dictionary")
def screenTone(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """접객 말투. 언제든, 안심, 살펴보세요, 하시면, 보여드립니다.

    왜: 화면은 손님을 맞는 점원이 아니다. 안심시키는 말 (언제든 바꿀 수 있습니다) 은 정보가 없고, 초대하는 말
        (준비된 회사부터 살펴보세요) 은 단추가 할 일을 글로 대신하며, 높이는 말 (로그인하시면 보여드립니다) 은 낱말이어야
        할 자리를 문장으로 늘린다. 사용자는 그 말을 읽지 않고 건너뛰거나, 읽고 나서 화면을 못 믿는다.
    어디서: 화면 낱말 규약 (운영 중인 세무 앱의 화면에서 실측, 2026-09-17, 운영자 지시).
    실측: 온보딩 "설정에서 언제든 지울 수 있습니다",
        "위하고에 로그인하시면 담당 수임처를 찾아 보여드립니다", "이렇게 부르겠습니다", 수집 화면 "준비된 회사부터 바로
        살펴보세요". 사전은 data/screenTone.toml 이고 설정의 dictionary.screenTone 으로 더한다.
    고치기: 지운다. 그 자리에 정보가 있었으면 낱말로 남긴다 (적지 않으셔도 됩니다 는 선택, 이렇게 부르겠습니다 는
        호칭 미리보기). 문장이 허용된 글에서도 같은 말은 사족이라 enforceStyle 로 켜서 잰다.
    안 잡는 것: 사전에 없는 말투. 보고서와 장표의 권고 (받으십시오) 는 초대가 아니라 조치라 사전에 없다. 프리셋 screen
        밖에서는 enforceStyle 에 넣어야 돈다.
    """
    yield from firstMatchFindings(doc, "screenTone", "screenTone")
