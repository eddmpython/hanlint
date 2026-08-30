"""hanlint: 한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는 린터.

공개 표면은 이 파일 한 곳이다.

```python
from hanlint import lintText, lintFile, auditText, fingerprint

findings = lintFile("글.md")       # list[Finding]
shape = auditText(text)            # AuditResult. 점수 없이 분포와 자리
prints = fingerprint(text)         # DocumentPrint. 지문 그대로
```

합격과 불합격을 판정하지 않는다. 지적 목록이 비어 있다는 것은 세어서 잡히는 결함이 없다는 뜻이지 좋은
글이라는 뜻이 아니다.
"""

from __future__ import annotations

from pathlib import Path

from .audit import AuditResult, auditDocument
from .config import Config, loadConfig
from .document import parseMarkdown
from .fingerprint import DocumentPrint, buildFingerprint
from .learn import LearnedExemplar, learnExemplars
from .rules import Finding, ruleDoc, ruleNames, ruleSummary, runAll

__all__ = [
    "AuditResult",
    "Config",
    "DocumentPrint",
    "Finding",
    "LearnedExemplar",
    "auditFile",
    "auditText",
    "fingerprint",
    "lintFile",
    "lintText",
    "learnText",
    "loadConfig",
    "ruleDoc",
    "ruleNames",
    "ruleSummary",
]
__version__ = "0.0.7"


def fingerprint(text: str, config: Config | None = None, path: str | None = None) -> DocumentPrint:
    """글을 한 번 읽어 지문을 만든다."""
    config = config or Config()
    return buildFingerprint(parseMarkdown(text, path=path), config)


def lintText(text: str, config: Config | None = None, path: str | None = None) -> list[Finding]:
    """문자열을 검사해 줄 번호 순의 지적 목록을 준다."""
    config = config or Config()
    return runAll(fingerprint(text, config, path), config)


def lintFile(path: str | Path, config: Config | None = None) -> list[Finding]:
    """파일을 UTF-8 로 읽어 검사한다."""
    path = Path(path)
    return lintText(path.read_text(encoding="utf-8"), config, path=str(path))


def learnText(before: str, after: str, config: Config | None = None) -> tuple[LearnedExemplar, ...]:
    """앞뒤 문자열에서 사람이 승인할 본보기 후보를 찾는다."""
    config = config or Config()
    beforeDoc = fingerprint(before, config)
    afterDoc = fingerprint(after, config)
    return learnExemplars(beforeDoc, afterDoc, runAll(beforeDoc, config), runAll(afterDoc, config), config.preset)


def auditText(text: str, config: Config | None = None, path: str | None = None) -> AuditResult:
    """지문 열의 분포와 자리. 점수도 등급도 없다."""
    config = config or Config()
    return auditDocument(fingerprint(text, config, path), config)


def auditFile(path: str | Path, config: Config | None = None) -> AuditResult:
    path = Path(path)
    return auditText(path.read_text(encoding="utf-8"), config, path=str(path))
