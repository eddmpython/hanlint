from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, Finding
from ..registry import rule
from ..shared import overridingFindings


@rule("calqueFrame", mechanism="dictionary")
def calqueFrame(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """단어는 한국어인데 한국 사람이 그 뜻으로 쓰지 않는 동사와 앞말의 짝. `글에 잇지 못했어요`, `그 팀에 닿는 줄`.

    왜: 영어의 link, reach, render를 한국어 동사 하나로 옮기면 단어마다 사전에 있는데 문장은 한국 사람이 쓰지 않는
        말이 된다. 독자는 단어를 다 알아도 무슨 일이 있었는지 다시 묻는다. 실측: AI가 쓴 `캐스팅 장갑과 가는
        합사는 아직 원투 글에 잇지 못했어요.`를 읽은 사람이 `잇지`가 이상하다고 되물었다. `맡겼습니다`를 읽고는
        누구에게 맡겼는지 물었다.
    어디서: 실제 대화 기록에서 사람이 지적한 조어 48건과 사람이 받아들인 문장 53건. 사전은 data/calqueFrame.toml이고
        항목마다 동사와 그 앞말(`잇다`와 `글에`, `닿다`와 `팀에`)을 정규식으로 적는다. 받는 이, 장소, 관용구가 같은
        문장에 있으면 바른 말이 되는 항목은 unless로 그 문장을 넘긴다. 실측: 지적 48건 가운데 11건을 잡고, 받아들인
        53건과 공개된 글 7,123문장에서는 하나도 잡지 않는다. 기준 말뭉치 1,600편 225,350문장에서는 6건이 났다(이야기
        글의 `맡기다` 4건, 옛 글의 `-어 봄` 2건).
    고치기: 그 일에 한국 사람이 쓰는 말로 바꾼다. `글에 잇다`는 `글에 연결하다`로, `그 팀에 닿는 줄`은 `그 팀에
        해당하는 규칙`으로, `숫자가 그려지기 전`은 `숫자가 화면에 뜨기 전`으로 쓴다. `맡겼습니다`에는 누구에게 무엇을
        맡겼는지 쓴다. 기본 사전은 확인 권고라 문맥을 보고 정한다. 프로젝트가 설정의 dictionary.calqueFrame으로 더한
        짝은 오류로 낸다.
    안 잡는 것: 처음 쓴 조어 전부. 말뭉치에 있는지만으로는 새로 지은 말과 자연스러운 한국어를 가려낼 수 없었다.
        줄과 대를 잇는 것(`원줄 아래에 카드채비를 잇고`, `끼워 잇는 낚싯대`), 몸이나 물건이 닿는 것(`바닥에 닿은
        봉돌`), 받는 이나 장소가 같은 문장에 있는 `맡기다`(`네이버에 맡겼습니다`). 앞 문장에만 받는 이가 있는
        `맡기다`는 잡는다. 백틱과 따옴표 안의 인용. 설정의 protectedTerms와 겹치는 곳.
    """
    yield from overridingFindings(doc, "calqueFrame", "calqueFrame", builtinSeverity=NOTICE)
