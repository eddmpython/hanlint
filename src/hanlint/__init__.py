"""hanlint: 한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는 린터.

공개 표면은 이 파일 한 곳이다.

```python
from hanlint import (
    auditText, entailmentCases, evaluateEntailment, evidenceLedger, fingerprint,
    guardText, lintFile, lintText, rhetoricalBlueprint, writingPacket,
    loadPanelTrialSet, preparePanelSuite, summarizePanelJudgeConsistency,
)

findings = lintFile("글.md")       # list[Finding]
shape = auditText(text)            # AuditResult. 점수 없이 분포와 자리
prints = fingerprint(text)         # DocumentPrint. 지문 그대로
packet = writingPacket(text)       # 초안과 대조 자료와 고침 근거
guard = guardText(brief, text)     # 구조화 요구와 결과의 결정적 표면 계약
blueprint = rhetoricalBlueprint(brief)  # 원문 없는 종류별 구조 예산
evidence = evidenceLedger(brief)    # 사실별 고정 근거 연결과 해시 검증
cases = entailmentCases()           # gold를 뺀 사람 합의 한국어 근거 쌍
metrics = evaluateEntailment(predictions)  # 외부 평가기 예측과 기권 집계
trialSet = loadPanelTrialSet("trial-set.json")
suite = preparePanelSuite(trialSet["trials"], trialSet["studyId"], 42)
```

합격과 불합격을 판정하지 않는다. 지적 목록이 비어 있다는 것은 세어서 잡히는 결함이 없다는 뜻이지 좋은
글이라는 뜻이 아니다.
"""

from __future__ import annotations

from pathlib import Path

from .arena import (
    CONTENT_CHOICES,
    EVALUATOR_GROUPS,
    PANEL_DIMENSIONS,
    PANEL_PROTOCOL_REVISION,
    PANEL_RUBRIC,
    PANEL_RUBRIC_SHA256,
    PANEL_VERSION,
    BlindEvaluation,
    GenerationRecord,
    WritingTrial,
    adjudicatePanel,
    aggregateResults,
    checkedAdjudication,
    checkedJudgePredictions,
    checkedPanelSuite,
    checkedPanelTrialSet,
    evaluatePanelJudge,
    loadPanelTrialSet,
    prepareBlind,
    preparePanelJudgeCases,
    preparePanelSuite,
    preparePanelTrialSet,
    recordEvaluation,
    recordPanelReviewBatch,
    revealPanel,
    revealTrial,
    summarizePanelJudgeConsistency,
)
from .audit import AuditResult, auditDocument
from .blueprint import STRATEGIES, STRATEGY_ID, blueprintFor, rhetoricalBlueprint
from .config import AtomicFact, Config, EvidenceRecord, WritingBrief, loadConfig, loadWritingBrief
from .document import parseMarkdown
from .entailment import (
    EntailmentEvaluationResult,
    EntailmentPrediction,
    EntailmentPredictions,
    entailmentCases,
    evaluateEntailment,
)
from .evidence import EvidenceLedgerResult, evidenceLedger
from .fingerprint import DocumentPrint, buildFingerprint
from .guard import GuardResult, guardFile, guardText
from .learn import LearnedExemplar, LearnedOperation, learnExemplars, learnOperations
from .report import buildBriefWritingPacket, buildWritingPacket
from .rules import Finding, ruleDoc, ruleNames, ruleSummary, runAll

__all__ = [
    "AuditResult",
    "AtomicFact",
    "BlindEvaluation",
    "CONTENT_CHOICES",
    "Config",
    "DocumentPrint",
    "EvidenceLedgerResult",
    "EvidenceRecord",
    "EntailmentEvaluationResult",
    "EntailmentPrediction",
    "EntailmentPredictions",
    "Finding",
    "GuardResult",
    "GenerationRecord",
    "EVALUATOR_GROUPS",
    "LearnedExemplar",
    "LearnedOperation",
    "WritingBrief",
    "WritingTrial",
    "PANEL_DIMENSIONS",
    "PANEL_PROTOCOL_REVISION",
    "PANEL_RUBRIC",
    "PANEL_RUBRIC_SHA256",
    "PANEL_VERSION",
    "STRATEGIES",
    "STRATEGY_ID",
    "aggregateResults",
    "adjudicatePanel",
    "auditFile",
    "auditText",
    "blueprintFor",
    "checkedAdjudication",
    "checkedJudgePredictions",
    "checkedPanelSuite",
    "checkedPanelTrialSet",
    "evidenceLedger",
    "entailmentCases",
    "evaluateEntailment",
    "evaluatePanelJudge",
    "fingerprint",
    "guardFile",
    "guardText",
    "lintFile",
    "lintText",
    "learnText",
    "learnOperationText",
    "loadConfig",
    "loadPanelTrialSet",
    "loadWritingBrief",
    "prepareBlind",
    "preparePanelJudgeCases",
    "preparePanelSuite",
    "preparePanelTrialSet",
    "recordEvaluation",
    "recordPanelReviewBatch",
    "revealPanel",
    "summarizePanelJudgeConsistency",
    "rhetoricalBlueprint",
    "revealTrial",
    "ruleDoc",
    "ruleNames",
    "ruleSummary",
    "writingPacket",
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
    """앞뒤 문자열에서 사람이 승인할 정확 재생 패치 후보를 찾는다."""
    config = config or Config()
    beforeDoc = fingerprint(before, config)
    afterDoc = fingerprint(after, config)
    return learnExemplars(beforeDoc, afterDoc, runAll(beforeDoc, config), runAll(afterDoc, config), config.preset)


def learnOperationText(before: str, after: str, config: Config | None = None) -> tuple[LearnedOperation, ...]:
    """앞뒤 문자열의 일대일 고침에서 사람이 승인할 표면 치환 후보를 찾는다."""
    config = config or Config()
    return learnOperations(fingerprint(before, config), fingerprint(after, config), config.preset, config.protectedTerms)


def writingPacket(
    text: str | WritingBrief | dict,
    config: Config | None = None,
    path: str | None = None,
    purpose: str = "revise",
    includeSource: bool = True,
    strategy: str | None = None,
) -> dict:
    """초안과 지문과 대조 자료와 고침 근거를 AI용 결정적 계약으로 묶는다."""
    if isinstance(text, dict):
        text = WritingBrief.fromMapping(text)
    if isinstance(text, WritingBrief):
        if purpose != "draft":
            raise ValueError("구조화 writing brief 는 purpose draft 에서만 쓴다")
        return buildBriefWritingPacket(text, path, includeSource, strategy)
    if not isinstance(text, str):
        raise ValueError("writingPacket 입력은 문자열, WritingBrief 또는 brief JSON 객체다")
    if strategy is not None:
        raise ValueError("작법 전략은 구조화 writing brief draft 에서만 쓴다")
    config = config or Config()
    doc = fingerprint(text, config, path)
    findings = runAll(doc, config)
    audit = auditDocument(doc, config)
    return buildWritingPacket(text, doc, findings, audit, config, purpose, includeSource)


def auditText(text: str, config: Config | None = None, path: str | None = None) -> AuditResult:
    """지문 열의 분포와 자리. 점수도 등급도 없다."""
    config = config or Config()
    return auditDocument(fingerprint(text, config, path), config)


def auditFile(path: str | Path, config: Config | None = None) -> AuditResult:
    path = Path(path)
    return auditText(path.read_text(encoding="utf-8"), config, path=str(path))
