"""README 첫 화면의 대표 출력이 실제 hanlint 출력과 같은지 본다.

README 는 이 도구를 처음 보는 사람이 읽는 첫 화면이고, 거기 붙은 출력 예시는 제품의 실제 동작을
베낀 것이다. 규칙 문구나 세는 방법을 고치면 조용히 어긋난다. 실측: 2026-08-31 에 doublePassive 의
이유 문구가 낡았고 (`피동 하나로 줄인다`), nounPile 이 세는 명사가 5개로 적혀 있었는데 실제는 6개였다.
"""

from __future__ import annotations

import re
from pathlib import Path

from hanlint import Config, lintText

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
# README 예시가 검사하는 그 글. 줄 번호가 예시와 맞아야 하므로 빈 줄까지 같다.
SAMPLE = "결과가 저장되어집니다.\n\n가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.\n"


def exampleBlock() -> str:
    blocks = re.findall(r"```text\n(.*?)```", README.read_text(encoding="utf-8"), re.DOTALL)
    for block in blocks:
        if block.startswith("설정:") and "[doublePassive]" in block:
            return block
    raise AssertionError("README 에서 대표 출력 예시 블록을 못 찾았다")


def testExampleMatchesRealFindings():
    block = exampleBlock()
    findings = list(lintText(SAMPLE, Config(), "글.md"))
    assert findings, "표본 글에서 지적이 나오지 않는다"
    for finding in findings:
        assert f"글.md:{finding.line}  [{finding.rule}]" in block, f"예시에 없는 지적: {finding.rule} {finding.line}번째 줄"
        assert finding.why in block, f"예시의 이유 문구가 낡았다. 지금 문구는:\n  {finding.why}"
        if finding.fix is not None:
            assert f"고친 뒤: {finding.fix}" in block, f"예시의 고침이 낡았다. 지금 고침은:\n  {finding.fix}"


def testExampleCountsMatch():
    findings = list(lintText(SAMPLE, Config(), "글.md"))
    errors = [finding for finding in findings if finding.severity == "error"]
    notices = [finding for finding in findings if finding.severity != "error"]
    block = exampleBlock()
    assert f"글.md  집은 자리 {len(errors)}" in block, f"머리줄의 error 수가 실제 {len(errors)}건과 다르다"
    if not notices:
        assert "확인할 자리" not in block, "예시에 없는 확인할 자리 를 머리줄이 말한다"
