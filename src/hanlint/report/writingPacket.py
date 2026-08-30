"""AI 작문기가 같은 근거로 초안을 쓰고 고치게 하는 결정적 JSON 계약.

잘 쓴 글을 복사하지 않는다. 현재 글의 지문과 같은 종류의 편집 글 분포, 독자 상태, 실제 지적과 승인 고침을
분리해 싣는다. 분포는 품질 점수가 아니다. 의미 고침은 원문 완전 일치에서만 재생하고, 승인 표면 치환은
단어 경계와 보호 원자가 맞는 다른 원문 한 자리까지 쓴다. 일반 문형 예시는 여러 프리셋의 사실을 결과에
흘린 완성 글 실측 때문에 실행 패킷에 싣지 않는다.
"""

from __future__ import annotations

import json
from hashlib import sha256

from ..audit import AuditResult
from ..blueprint import blueprintFor
from ..config import PROFILE_OF, Config, WritingBrief
from ..data.profiles import Histogram, Profile, profileOf, userProfile
from ..fingerprint import DocumentPrint
from ..rules import Finding
from .operationMatch import operationGuidance
from .patchMatch import patchData

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
            "guidance.patch는 글쓴이가 승인했고 match의 원문, 프리셋, 국소 표지와 독자 상태가 현재 자리에 모두 맞는 고침이다",
            "guidance.patch가 있으면 현재 문장 전체를 patch.after로 바꾸고 비슷한 다른 문장에는 일반화하지 않는다",
            "guidance.patch가 없는 지적에는 다른 본보기를 끌어오지 말고 확실하지 않으면 원문을 둔다",
            "guidance.patch.after의 이름과 수치와 사실을 다른 문장으로 확산하거나 없는 정보를 만들어 채우지 않는다",
            "guidance.operation은 승인 전후의 32자 이하 표면 치환이다. "
            "sourceText 한 자리와 단어 경계와 보호 원자가 맞을 때만 result를 쓴다",
            "guidance.operation이 없으면 비슷한 단어나 의미를 추측해 치환하지 않는다",
            "referenceProfile은 같은 종류 글의 분포이며 품질 점수나 평균을 흉내 내라는 명령이 아니다",
            "comparison의 수치와 문구는 진단 자료다. 결과 글의 사실이나 문장 재료로 옮기지 않는다",
            "설명 없이 완성된 한국어 마크다운만 결과로 낸다",
        ],
        "completion": [
            "결과를 다시 hanlint로 검사해 새 error가 생기지 않았는지 확인한다",
            "error 0은 세어서 잡히는 결함이 없다는 뜻뿐이므로 사실과 뜻과 유용성은 사람이나 평가자가 확인한다",
        ],
    }


def briefContractFor() -> dict:
    return {
        "operation": "input.brief의 원자 사실만 사용해 독자의 과업을 끝내는 한국어 마크다운 초안을 쓴다",
        "constraints": [
            "input.brief 밖의 사실, 수치, 이름, URL, 코드, 인과와 배경을 만들지 않는다",
            "facts의 id는 대조용 표지다. 결과 글에는 id나 사실 원장이라는 말을 쓰지 않는다",
            "mustInclude의 표면과 allowedNumbers의 숫자를 모두 보존한다",
            "forbidden의 문자열 표면을 쓰지 않는다",
            "length의 min과 max 사이에서 완결된 글을 쓴다",
            "설명, 자기평가와 작성 과정 없이 완성된 한국어 마크다운만 결과로 낸다",
        ],
        "completion": [
            "결과를 verify.argv의 hanlint guard로 검사한다",
            "guard 위반을 자동 재작성하지 말고 원문과 대조해 한 자리씩 고친다",
            "guard 충족은 원자 사실의 관계와 진실, 금지 주장의 바꿔 말하기, 독자 효용과 자연스러움을 보장하지 않는다",
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
    guidance: list[dict] = []
    for finding in findings:
        selected = patchData(doc, finding, config.preset, config.patches)
        if selected:
            guidance.append({"rule": finding.rule, "line": finding.line, "patch": selected})
    guidance.extend(operationGuidance(doc, findings, config.preset, config.operations, config.patches, config.protectedTerms))
    return sorted(guidance, key=lambda item: (item["line"], "operation" in item))


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
        "version": 2,
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
        "guidance": guidanceFor(doc, findings, config) if purpose == "revise" else [],
        "verify": {
            "argv": [
                "hanlint",
                doc.path if purpose == "revise" and doc.path else "<output.md>",
                "--preset",
                config.preset,
                "--format",
                "json",
            ],
            "meaning": "error 0은 자동 결함이 없다는 뜻뿐이다. writingPacket은 자연스러움과 사실 보존과 "
            "유용성의 향상을 보장하지 않으므로 원문 대조와 별도 평가가 필요하다",
        },
    }


def buildBriefWritingPacket(
    brief: WritingBrief,
    path: str | None = None,
    includeSource: bool = True,
    strategy: str | None = None,
) -> dict:
    """구조화 brief만 사실 재료로 둔 draft 실행 패킷."""
    inputData: dict = {
        "kind": "hanlint.writingBrief",
        "path": path,
        "preset": brief.preset,
        "briefSha256": brief.digest,
    }
    if includeSource:
        inputData["brief"] = brief.asDict()
    packet = {
        "version": 2,
        "kind": "hanlint.writingPacket",
        "purpose": "draft",
        "contract": briefContractFor(),
        "input": inputData,
        "findings": {"errorCount": 0, "noticeCount": 0, "items": []},
        "guidance": [],
        "verify": {
            "argv": ["hanlint", "guard", path or "<brief.json>", "<output.md>", "--format", "json"],
            "meaning": "guard는 명시한 표면과 자동 error만 확인한다. 사실 관계와 진실, 유용성과 "
            "자연스러움은 원문 대조와 별도 평가가 필요하다",
        },
    }
    if strategy is not None:
        packet["strategy"] = blueprintFor(brief, strategy)
        packet["contract"]["constraints"].extend(
            (
                "strategy.budget은 원문 없는 구조 예산이다. brief.length를 우선하며 절, 문단과 문장 수의 개요로만 쓴다",
                "strategy.reference의 수치, 해시와 sourceIds를 결과 글의 사실이나 문장 재료로 옮기지 않는다",
            )
        )
    return packet


def renderWritingPacket(packet: dict) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2)
