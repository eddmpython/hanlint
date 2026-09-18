"""공용 fixture. 글에서 지적까지 한 번에 가는 도우미와 fixture 의 자리표시자."""

from __future__ import annotations

import sys

import pytest

# 어떻게 불려도 저장소 안에 __pycache__ 를 남기지 않는다. `-B` 없이 pytest 를 돌린 흔적이 실제로 남았다 (2026-09-17).
# 이 줄 뒤에 import 되는 모듈 (hanlint 와 테스트 모듈) 은 바이트코드를 쓰지 않는다. 잔해는 testNoBytecodeCache 가 잡는다.
sys.dont_write_bytecode = True

from hanlint.config import Config  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402
from hanlint.fingerprint import buildFingerprint  # noqa: E402
from hanlint.rules import runAll  # noqa: E402

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
