from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, Finding
from ..registry import rule
from ..shared import overridingFindings


@rule("calqueFrame", mechanism="dictionary")
def calqueFrame(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """낱말은 한국어인데 한국 사람이 그 뜻으로 쓰지 않는 동사와 앞말의 짝. `글에 잇지 못했어요`, `그 팀에 닿는 줄`.

    왜: 영어의 link, reach, render 를 한국어 동사 하나로 옮기면 낱말마다 사전에 있는데 문장은 한국 사람이 쓰지 않는
        말이 된다. 독자는 낱말을 다 알아도 무슨 일이 있었는지 다시 묻는다. 실측: AI 세션이 쓴 `캐스팅 장갑과 가는
        합사는 아직 원투 글에 잇지 못했어요.` 를 읽은 운영자가 `글에 잇지 못했다 에서 잇지 말이 이상하단생각안하나`
        라고 되물었다 (돈값, 2026-10-29). `맡겼습니다` 에는 `누구한테맡기나??` 라고 물었다 (2026-10-23).
    어디서: 돈값 회사 기록에서 운영자가 지적한 조어 48건과 운영자가 받아들인 문장 53건 (2026-11-01). 사전은
        data/calqueFrame.toml 이고 항목마다 동사와 그 앞말 (잇다 와 글에, 닿다 와 팀에) 을 정규식으로 적는다. 같은
        문장의 다른 자리 (받는 이, 장소, 관용구) 가 있으면 정상인 항목은 unless 로 그 문장을 넘긴다. 실측: 지적 48건
        가운데 11건을 잡고, 받아들인 53건과 돈값 공개 글 7,123문장에서는 하나도 잡지 않는다. 기준 말뭉치 1,600편
        225,350문장에서는 6건이 났다 (서사의 맡기다 4건, 옛 글의 -어 봄 2건).
    고치기: 그 일에 한국 사람이 쓰는 말로 바꾼다. 글에 잇다 는 글에 연결하다, 그 팀에 닿는 줄 은 그 팀에 해당하는
        규칙, 숫자가 그려지기 전 은 숫자가 화면에 뜨기 전, 맡겼습니다 는 누구에게 무엇을 맡겼는지 쓴다. 기본 사전은
        notice 라 문맥을 보고 정한다. 프로젝트가 설정의 dictionary.calqueFrame 으로 더한 짝은 error 다.
    안 잡는 것: 처음 쓴 조어 전부. 말뭉치에 있는지로는 처음 쓴 조어와 자연스러운 한국어가 갈리지 않았다
        (start.product 의 잡지 않는 것). 줄과 대를 잇는 것 (원줄 아래에 카드채비를 잇고, 끼워 잇는 낚싯대), 몸이나
        물건이 닿는 것 (바닥에 닿은 봉돌), 받는 이나 장소가 같은 문장에 있는 맡기다 (네이버에 맡겼습니다). 앞 문장에만
        받는 이가 있는 맡기다는 잡는다. 백틱과 따옴표 안의 인용. 설정의 protectedTerms 와 겹치는 자리.
    """
    yield from overridingFindings(doc, "calqueFrame", "calqueFrame", builtinSeverity=NOTICE)
