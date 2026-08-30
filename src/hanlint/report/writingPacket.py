"""AI 작문기가 같은 근거로 초안을 쓰고 고치게 하는 결정적 JSON 계약.

잘 쓴 글을 복사하지 않는다. 현재 글의 지문과 같은 종류의 편집 글 분포, 독자 상태, 실제 지적, 검증된
본보기와 문형을 분리해 싣는다. 분포는 품질 점수가 아니며 본보기의 `before` 는 따라 쓸 문장이 아니다.
"""

from __future__ import annotations

import json
from hashlib import sha256

from ..audit import AuditResult
from ..config import PROFILE_OF, Config
from ..data import exemplarFor, patterns
from ..data.profiles import Histogram, Profile, profileOf, userProfile
from ..fingerprint import DocumentPrint
from ..rules import Finding
from .registerMatch import exemplarInRegister, patternInRegister

PURPOSES = ("draft", "revise")


def jsonReady(value):
    """tuple까지 JSON 배열로 바꿔 공개 함수의 반환값과 직렬화 뒤 값을 같게 한다."""
    if isinstance(value, dict):
        return {key: jsonReady(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonReady(item) for item in value]
    return value


def percentilesOf(histogram: Histogram | None) -> dict[str, int]:
    if histogram is None:
        return {}
    return {f"p{percentile}": value for percentile, value in histogram.percentiles.items()}


def referenceProfile(config: Config) -> tuple[Profile | None, str | None]:
    if config.profile:
        return userProfile(config.profile), config.profile
    kind = PROFILE_OF.get(config.preset)
    return (profileOf(kind), f"bundled:{kind}") if kind else (None, None)


def compactProfile(config: Config) -> dict | None:
    profile, source = referenceProfile(config)
    if profile is None:
        return None
    return {
        "source": source,
        "kind": profile.kind,
        "label": profile.label,
        "documents": profile.documents,
        "sentences": profile.sentences,
        "paragraphs": profile.paragraphs,
        "sentencePercentiles": {name: percentilesOf(histogram) for name, histogram in sorted(profile.sentence.items())},
        "paragraphPercentiles": {name: percentilesOf(histogram) for name, histogram in sorted(profile.paragraph.items())},
        "endingRunPercentiles": percentilesOf(profile.endingRuns),
        "rates": profile.rates,
    }


def contractFor(purpose: str) -> dict:
    if purpose not in PURPOSES:
        raise ValueError(f"purpose 는 {', '.join(PURPOSES)} 가운데 하나다: {purpose}")
    if purpose == "draft":
        operation = "input.text를 요구사항으로 읽고 새 한국어 마크다운 초안을 쓴다"
        preservation = "요구사항에 없는 사실과 수치와 출처를 만들지 않는다"
        findingUse = "findings는 요구사항 문구에서 찾은 피할 꼴로만 참고하고 요구사항 자체를 결과로 고치지 않는다"
    else:
        operation = "input.text의 한국어 마크다운 초안을 고친다"
        preservation = "원문의 사실, 수치, 고유명사, 링크, 코드와 조건을 보존한다"
        findingUse = "findings의 정확한 자리부터 고치고 다른 문장을 불필요하게 다시 쓰지 않는다"
    return {
        "operation": operation,
        "constraints": [
            preservation,
            findingUse,
            "guidance.exemplar.after는 변환 방법만 본뜨며 문구를 복사하지 않는다",
            "patterns에서는 form과 example만 쓰고 instead는 피한다",
            "referenceProfile은 같은 종류 글의 분포이며 품질 점수나 평균을 흉내 내라는 명령이 아니다",
            "설명 없이 완성된 한국어 마크다운만 결과로 낸다",
        ],
        "completion": [
            "결과를 다시 hanlint로 검사해 새 error가 생기지 않았는지 확인한다",
            "error 0은 세어서 잡히는 결함이 없다는 뜻뿐이므로 사실과 뜻과 유용성은 사람이나 평가자가 확인한다",
        ],
    }


def readerState(doc: DocumentPrint, audit: AuditResult) -> dict:
    final = doc.reader.final
    return {
        "recentTopics": sorted(final.recent),
        "knownTopicCount": len(final.known),
        "frequentTopics": [[word, count] for word, count in audit.lexicon.topWords],
        "numbersSeen": sorted(final.numerals),
        "filesCreated": sorted(final.files),
        "promises": [[line, text] for line, text in final.promises],
        "recalls": [[line, text] for line, text in final.recalls],
    }


def guidanceFor(doc: DocumentPrint, findings: list[Finding], config: Config) -> list[dict]:
    names = {finding.rule for finding in findings} | {exemplar.rule for exemplar in config.exemplars}
    guidance: list[dict] = []
    for name in sorted(names):
        exemplar = exemplarFor(name, config.preset, config.exemplars)
        if exemplar:
            guidance.append({"rule": name, "exemplar": exemplarInRegister(exemplar, doc.register).asDict()})
    return guidance


def buildWritingPacket(
    text: str,
    doc: DocumentPrint,
    findings: list[Finding],
    audit: AuditResult,
    config: Config,
    purpose: str = "revise",
    includeSource: bool = True,
) -> dict:
    inputData: dict = {
        "path": doc.path,
        "preset": config.preset,
        "register": doc.register,
        "frontmatter": dict(doc.frontmatter),
        "textSha256": sha256(text.encode()).hexdigest(),
    }
    if includeSource:
        inputData["text"] = text
    errors = sum(finding.severity == "error" for finding in findings)
    notices = len(findings) - errors
    return {
        "version": 1,
        "kind": "hanlint.writingPacket",
        "purpose": purpose,
        "contract": contractFor(purpose),
        "input": inputData,
        "comparison": {
            "current": jsonReady(audit.asDict()),
            "referenceProfile": compactProfile(config),
            "readerState": readerState(doc, audit),
        },
        "findings": {
            "errorCount": errors,
            "noticeCount": notices,
            "items": [finding.asDict() for finding in findings],
        },
        "guidance": guidanceFor(doc, findings, config),
        "patterns": [patternInRegister(pattern, doc.register).asDict() for pattern in patterns()],
        "verify": {
            "argv": [
                "hanlint",
                doc.path if purpose == "revise" and doc.path else "<output.md>",
                "--preset",
                config.preset,
                "--format",
                "json",
            ],
            "meaning": "error 0은 자동으로 확인할 수 있다. 좋은 글과 뜻 보존은 별도 평가다",
        },
    }


def renderWritingPacket(packet: dict) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2)
