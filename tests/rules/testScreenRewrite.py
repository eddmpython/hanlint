"""화면 문장의 고침 제안. 사전 항목의 to 규칙이 문장 전체를 낱말로 다시 쓴다. npm/test/screenRewrite.test.js 와 같은 사례다."""

from __future__ import annotations

import pytest

from hanlint.config import Config
from hanlint.document import parseMarkdown
from hanlint.fingerprint import buildFingerprint
from hanlint.rules import runAll

CONFIG = Config(preset="screen")

REWRITES = [
    ("요청을 완료하지 못했습니다", "요청 완료 실패"),
    ("상태를 확인하지 못했습니다.", "상태 확인 실패"),
    ("저장되지 않았습니다", "저장 실패"),
    ("자료를 불러오지 못했습니다", "자료 불러오기 실패"),
    ("기존 기록을 읽지 못했습니다.", "기존 기록 읽기 실패"),
    ("대시보드를 열고 있습니다", "대시보드 여는 중"),
    ("파일을 만들고 있습니다", "파일 만드는 중"),
    ("GitHub에 연결하고 있어요.", "GitHub에 연결하는 중"),
    ("수정한 문장을 다시 읽고 있어요.", "수정한 문장을 다시 읽는 중"),
    ("자료 갱신을 위한 로그인이 필요합니다", "자료 갱신을 위한 로그인 필요"),
    ("먼저 원고를 저장해야 합니다", "먼저 원고 저장 필요"),
    ("변경을 완료했습니다", "변경 완료됨"),
    ("수정본을 기록했습니다.", "수정본 기록됨"),
    ("저장되었습니다", "저장됨"),
    ("검사가 끝났습니다", "검사 완료"),
]

NO_PROPOSAL = [
    "아이디와 비밀번호를 모두 입력해 주세요",
    "같은 수정본이 이미 기록되어 있어요.",
    "이 파일이 지금 배포 중인 것과 다르다.",
]


def screenSentence(text: str):
    findings = [f for f in runAll(buildFingerprint(parseMarkdown(text), CONFIG), CONFIG) if f.rule == "screenSentence"]
    assert len(findings) == 1, text
    return findings[0]


@pytest.mark.parametrize(("text", "expected"), REWRITES)
def testProgressFailureNeedAndDoneBecomeWords(text: str, expected: str):
    finding = screenSentence(text)
    assert finding.fix == expected
    assert finding.fragment and finding.replacement is not None
    assert text.replace(finding.fragment, finding.replacement, 1) == expected


@pytest.mark.parametrize("text", NO_PROPOSAL)
def testMeaningChoicesStayWithThePerson(text: str):
    """입력 요청과 일반 종결어미는 뜻을 골라야 하므로 제안이 없다. 지적은 그대로다."""
    finding = screenSentence(text)
    assert finding.fix is None and finding.fragment is None and finding.replacement is None
