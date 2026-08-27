"""공용 fixture. 분석기는 세션에서 한 번만 만든다. kiwi 는 설치됐을 때만 목록에 든다."""

from __future__ import annotations

import pytest

from hanlint.analysis import SurfaceAnalyzer, makeAnalyzer
from hanlint.config import Config
from hanlint.document import parseMarkdown
from hanlint.fingerprint import buildFingerprint
from hanlint.rules import runAll

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)


def availableAnalyzers():
    analyzers = [SurfaceAnalyzer()]
    try:
        import kiwipiepy  # noqa: F401

        analyzers.append(makeAnalyzer("kiwi"))
    except ImportError:
        pass
    return analyzers


ANALYZERS = availableAnalyzers()


def expandTokens(text: str) -> str:
    """fixture 의 자리표시자. 대시는 게이트에 걸려 파일에 못 두고, 명령형 뒤 마침표는 훅이 막는다."""
    return text.replace("{em}", EM_DASH).replace("{en}", EN_DASH).replace("{dot}", ".")


def findingsOf(text: str, config: Config | None = None, analyzer=None):
    config = config or Config()
    analyzer = analyzer or ANALYZERS[0]
    return runAll(buildFingerprint(parseMarkdown(text), analyzer, config), config)


@pytest.fixture(params=ANALYZERS, ids=lambda a: a.name)
def analyzer(request):
    return request.param


@pytest.fixture
def rulesOf():
    def run(text: str, config: Config | None = None, analyzer=None) -> list[str]:
        return [f.rule for f in findingsOf(expandTokens(text), config, analyzer)]

    return run
