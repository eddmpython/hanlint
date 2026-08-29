"""공용 fixture. 글에서 지적까지 한 번에 가는 도우미와 fixture 의 자리표시자."""

from __future__ import annotations

import pytest

from hanlint.config import Config
from hanlint.document import parseMarkdown
from hanlint.fingerprint import buildFingerprint
from hanlint.rules import runAll

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)


def expandTokens(text: str) -> str:
    """fixture 의 자리표시자. 대시는 게이트에 걸려 파일에 못 두고, 명령형 뒤 마침표는 훅이 막는다."""
    return text.replace("{em}", EM_DASH).replace("{en}", EN_DASH).replace("{dot}", ".")


def findingsOf(text: str, config: Config | None = None):
    config = config or Config()
    return runAll(buildFingerprint(parseMarkdown(text), config), config)


@pytest.fixture
def rulesOf():
    def run(text: str, config: Config | None = None) -> list[str]:
        return [f.rule for f in findingsOf(expandTokens(text), config)]

    return run
