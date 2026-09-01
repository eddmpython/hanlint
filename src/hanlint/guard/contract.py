"""Reader Contract 검사와 이유가 붙은 국소 Patch 검증."""

from __future__ import annotations

from collections import Counter
from copy import copy
from hashlib import sha256

from ..config import Config, Contract, ContractV2, Outline, Patch, parseContract
from ..document import parseMarkdown
from ..fingerprint import buildFingerprint
from ..rules import Finding, runAll
from .outline import compareOutline, summarizeDocument
from .receipt import CheckResult, PatchResult
from .surface import factLines, protectedSurface, surfaceDiff


def contractFromText(text: str, reader: str, goal: str) -> Contract:
    """원문의 보호 표면을 모두 덮는 version 1 Contract 초안을 만든다."""
    contract = Contract(reader, goal, factLines(text))
    result = surfaceDiff(contract.text, text)
    missing = []
    for kind in ("missingNumbers", "missingUrls", "missingCode", "missingLinks"):
        missing.extend(f"{kind}={value}" for value in getattr(result, kind))
    if missing:
        raise ValueError("reader 또는 goal이 원문에 없는 보호 원자를 넣었다: " + ", ".join(missing))
    if result.violationCount:
        issues = [f"{kind}={value}" for kind, values in result.asDict().items() for value in values]
        raise RuntimeError("계약 초안이 원문의 보호 표면을 모두 담지 못했다: " + ", ".join(issues))
    return contract


def contractFromTextV2(
    text: str,
    reader: str,
    goal: str,
    outlineLevel: int = 2,
    facts: list[str] | tuple[str, ...] = (),
) -> ContractV2:
    """원문의 자동 표면과 한 수준의 제목을 분리한 version 2 Contract 초안을 만든다."""
    document = parseMarkdown(text)
    headings = tuple(heading.text for heading in document.headings(outlineLevel))
    contract = ContractV2(reader, goal, facts, protectedSurface(text), Outline(outlineLevel, headings))
    result = surfaceDiff(contract.text, text)
    if result.violationCount:
        issues = [f"{kind}={value}" for kind, values in result.asDict().items() for value in values]
        raise ValueError("reader, goal 또는 facts가 원문에 없는 보호 원자를 넣었다: " + ", ".join(issues))
    return contract


def check(
    text: str,
    contract: Contract | ContractV2 | dict,
    config: Config | None = None,
    path: str | None = None,
) -> CheckResult:
    """글을 바꾸지 않고 Reader Contract 보호 원자와 hanlint 지적을 계산한다."""
    if isinstance(contract, dict):
        contract = parseContract(contract)
    if not isinstance(contract, (Contract, ContractV2)):
        raise ValueError("contract 는 Contract 또는 contract JSON 객체다")
    selectedConfig = copy(config) if config is not None else Config()
    doc = buildFingerprint(parseMarkdown(text, path=path), selectedConfig)
    findings = tuple(runAll(doc, selectedConfig))
    outline = compareOutline(contract.outline, doc) if isinstance(contract, ContractV2) else None
    document = summarizeDocument(doc) if isinstance(contract, ContractV2) else None
    return CheckResult(
        contractSha256=contract.digest,
        draftSha256=sha256(text.encode()).hexdigest(),
        surface=surfaceDiff(contract.text, text),
        findings=findings,
        contractVersion=contract.version,
        outline=outline,
        document=document,
    )


def contractIssues(result: CheckResult) -> set[tuple[str, str]]:
    issues = {(kind, value) for kind, values in result.surface.asDict().items() for value in values}
    if result.outline is not None:
        issues.update(("outline", mismatch.signature) for mismatch in result.outline.mismatches)
    return issues


def reasonCount(result: CheckResult, reason: str) -> int:
    surface = result.surface.asDict()
    if reason in surface:
        return len(surface[reason])
    if reason == "outline" and result.outline is not None:
        return result.outline.violationCount
    return sum(finding.rule == reason for finding in result.findings)


def errorSignature(finding: Finding) -> tuple[str, str]:
    return finding.rule, finding.quote


def addedErrors(before: CheckResult, after: CheckResult) -> tuple[Finding, ...]:
    remaining = Counter(errorSignature(finding) for finding in before.findings if finding.severity == "error")
    added = []
    for finding in after.findings:
        if finding.severity != "error":
            continue
        signature = errorSignature(finding)
        if remaining[signature]:
            remaining[signature] -= 1
        else:
            added.append(finding)
    return tuple(added)


def verifyPatch(
    text: str,
    patch: Patch | dict,
    contract: Contract | ContractV2 | dict,
    config: Config | None = None,
    path: str | None = None,
) -> PatchResult:
    """원문은 바꾸지 않고 정확 Patch의 근거 감소와 새 위반 부재를 검증한다."""
    if isinstance(patch, dict):
        patch = Patch.fromMapping(patch)
    if not isinstance(patch, Patch):
        raise ValueError("patch 는 Patch 또는 patch JSON 객체다")
    if isinstance(contract, dict):
        contract = parseContract(contract)
    if not isinstance(contract, (Contract, ContractV2)):
        raise ValueError("contract 는 Contract 또는 contract JSON 객체다")
    beforeResult = check(text, contract, config, path)
    matchCount = text.count(patch.before)
    reasonBefore = reasonCount(beforeResult, patch.reason)
    if matchCount != 1:
        return PatchResult(
            contractSha256=contract.digest,
            sourceSha256=beforeResult.draftSha256,
            patchSha256=patch.digest,
            resultSha256=None,
            reason=patch.reason,
            matchCount=matchCount,
            reasonBefore=reasonBefore,
            reasonAfter=None,
            newContractIssues=(),
            newErrors=(),
            resultText=None,
            contractVersion=contract.version,
        )
    resultText = text.replace(patch.before, patch.after, 1)
    afterResult = check(resultText, contract, config, path)
    newContractIssues = tuple(sorted(contractIssues(afterResult) - contractIssues(beforeResult)))
    return PatchResult(
        contractSha256=contract.digest,
        sourceSha256=beforeResult.draftSha256,
        patchSha256=patch.digest,
        resultSha256=afterResult.draftSha256,
        reason=patch.reason,
        matchCount=matchCount,
        reasonBefore=reasonBefore,
        reasonAfter=reasonCount(afterResult, patch.reason),
        newContractIssues=newContractIssues,
        newErrors=addedErrors(beforeResult, afterResult),
        resultText=resultText,
        contractVersion=contract.version,
    )


__all__ = ["check", "contractFromText", "contractFromTextV2", "verifyPatch"]
