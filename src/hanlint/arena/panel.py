"""사람 패널 합의와 자동 심사기 보정을 위한 블라인드 작문 아레나."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from random import Random

from ..config import Config
from . import (
    WritingTrial,
    candidateIsLeft,
    checkedSha,
    checkedString,
    checkedText,
    exactKeys,
    loadJson,
    prepareBlind,
    stableDigest,
)

PANEL_VERSION = 1
PANEL_PROTOCOL_REVISION = "hanlint.writingArena.panel.v1"
PANEL_DIMENSIONS = ("naturalness", "clarity", "taskUtility", "voice")
PANEL_CHOICES = ("left", "right", "tie", "cannotJudge")
CONTENT_CHOICES = ("pass", "fail", "cannotJudge")
CONSENSUS_CHOICES = ("left", "right", "tie", "noConsensus", "ineligible")
EVALUATOR_GROUPS = ("targetReader", "professionalEditor", "koreanExpert", "generalReader")
JUDGE_CHOICES = ("left", "right", "tie", "abstain")
JUDGE_CONTENT_CHOICES = ("pass", "fail", "abstain")

PANEL_RUBRIC = {
    "rubricId": "hanlint.writingArena.kr.v1",
    "contentCheck": (
        "왼쪽과 오른쪽을 각각 사실, 금지 주장, 요구 밖 수치와 독자 과업에 대조한다. "
        "하나라도 뜻을 바꾸거나 지어냈으면 fail, 근거가 모자라면 cannotJudge다"
    ),
    "dimensions": {
        "naturalness": "한국어 화자가 이 상황에서 쓴 글처럼 막힘 없이 읽히는 쪽을 고른다. 맞춤법만 세지 않는다",
        "clarity": "대상과 문장 사이 관계가 분명해 독자가 다시 풀어 읽지 않아도 되는 쪽을 고른다",
        "taskUtility": "명시된 독자가 과업을 실제로 끝내는 데 더 도움이 되는 쪽을 고른다",
        "voice": "제공된 목소리 표본의 어휘, 밀도, 종결과 강조 습관을 더 잘 보존한 쪽을 고른다",
    },
    "choices": {
        "preference": list(PANEL_CHOICES),
        "content": list(CONTENT_CHOICES),
    },
    "rules": [
        "생성 전략, 모델과 작성자를 추측하지 않는다",
        "두 글 모두 좋거나 차이가 없으면 tie를 고른다",
        "판단 자료가 없으면 cannotJudge를 고른다",
        "한쪽이라도 contentCheck가 pass가 아니면 네 선호를 모두 cannotJudge로 둔다",
        "목소리 표본이 없으면 voice는 cannotJudge다",
        "각 선택의 근거를 글의 구체적인 자리에 붙여 적는다",
    ],
}
PANEL_RUBRIC_SHA256 = stableDigest(PANEL_RUBRIC)


def preparePanelTrialSet(studyId: str, trials: list[WritingTrial | dict], provenance: dict) -> dict:
    """같은 후보 전략의 trial과 자료 경계를 하나의 재현 가능한 입력 계약으로 묶는다."""
    studyId = checkedString(studyId, "panel trial set studyId")
    parsed = [item if isinstance(item, WritingTrial) else WritingTrial.fromMapping(item) for item in trials]
    if not parsed:
        raise ValueError("panel trial set에는 writing trial이 하나 이상 필요하다")
    identifiers = [trial.id for trial in parsed]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("panel trial set의 trial id가 겹친다")
    strategies = {trial.candidate.strategyId for trial in parsed}
    if len(strategies) != 1:
        raise ValueError("panel trial set에는 같은 candidate strategy trial만 넣는다")
    provenance = exactKeys(
        provenance,
        {"origin", "license", "containsExternalReferenceText", "qualityLabels"},
        "panel trial set provenance",
    )
    checkedString(provenance["origin"], "panel trial set provenance.origin")
    checkedString(provenance["license"], "panel trial set provenance.license")
    for name in ("containsExternalReferenceText", "qualityLabels"):
        if not isinstance(provenance[name], bool):
            raise ValueError(f"panel trial set provenance.{name} 는 boolean이다")
    if provenance["qualityLabels"]:
        raise ValueError("panel trial set은 사람 품질 label을 담지 않는다. review batch로 따로 가져온다")
    if provenance["license"].casefold() in {"none", "unknown", "unspecified"}:
        raise ValueError("panel trial set provenance.license는 확인한 사용 조건을 적는다")
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelTrialSet",
        "studyId": studyId,
        "candidateStrategyId": next(iter(strategies)),
        "provenance": deepcopy(provenance),
        "trials": [trial.asDict() for trial in parsed],
        "claimBoundary": (
            "이 파일은 평가할 글 쌍과 자료 경계를 고정한다. qualityLabels가 false면 사람 선호나 향상 정답을 담지 않는다"
        ),
    }
    payload["trialSetSha256"] = digestWithout(payload, "trialSetSha256")
    return payload


def checkedPanelTrialSet(data: object) -> dict:
    """panel trial set의 닫힌 키, trial 해시와 자료 경계를 검증한다."""
    data = exactKeys(
        data,
        {
            "version",
            "kind",
            "studyId",
            "candidateStrategyId",
            "provenance",
            "trials",
            "claimBoundary",
            "trialSetSha256",
        },
        "panel trial set",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != "hanlint.panelTrialSet":
        raise ValueError("panel trial set의 version 또는 kind가 다르다")
    provenance = exactKeys(
        data["provenance"],
        {"origin", "license", "containsExternalReferenceText", "qualityLabels"},
        "panel trial set provenance",
    )
    checkedString(provenance["origin"], "panel trial set provenance.origin")
    checkedString(provenance["license"], "panel trial set provenance.license")
    if not isinstance(provenance["containsExternalReferenceText"], bool) or not isinstance(provenance["qualityLabels"], bool):
        raise ValueError("panel trial set provenance의 경계 표시는 boolean이다")
    if not isinstance(data["trials"], list):
        raise ValueError("panel trial set trials는 배열이다")
    expected = preparePanelTrialSet(data["studyId"], data["trials"], provenance)
    if data != expected:
        raise ValueError("panel trial set이 trial과 provenance에서 만든 고정 결과와 다르다")
    return data


def loadPanelTrialSet(path: str | Path) -> dict:
    return checkedPanelTrialSet(loadJson(path))


def checkedInteger(value: object, where: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{where} 는 {minimum} 이상의 정수다")
    return value


def checkedConfidence(value: object, where: str, abstained: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} 는 0 이상 1 이하 숫자다")
    normalized = float(value)
    if not 0 <= normalized <= 1:
        raise ValueError(f"{where} 는 0 이상 1 이하 숫자다")
    if abstained and normalized != 0:
        raise ValueError(f"{where} 는 기권이면 0이다")
    return normalized


def digestWithout(data: dict, key: str) -> str:
    canonical = deepcopy(data)
    canonical.pop(key, None)
    return stableDigest(canonical)


def suiteDigest(data: dict) -> str:
    canonical = deepcopy(data)
    canonical.pop("suiteSha256", None)
    if "reviewTemplate" in canonical:
        canonical["reviewTemplate"]["suiteSha256"] = "<suiteSha256>"
    return stableDigest(canonical)


def checkedVoiceReference(data: object, where: str = "voiceReference") -> dict | None:
    if data is None:
        return None
    data = exactKeys(data, {"text", "textSha256", "permission"}, where)
    text = checkedText(data["text"], f"{where}.text")
    if len(text) > 2000:
        raise ValueError(f"{where}.text 는 2,000자 이하다")
    textSha = checkedSha(data["textSha256"], f"{where}.textSha256")
    if sha256(text.encode()).hexdigest() != textSha:
        raise ValueError(f"{where}.textSha256 가 text와 다르다")
    if data["permission"] != "evaluationOnly":
        raise ValueError(f"{where}.permission 은 evaluationOnly다")
    return {"text": text, "textSha256": textSha, "permission": "evaluationOnly"}


def evaluationContext(trial: WritingTrial, voiceReference: dict | None) -> dict:
    brief = trial.brief
    return {
        "genre": brief.preset,
        "reader": brief.reader,
        "task": brief.task,
        "facts": [fact.asDict() for fact in brief.facts],
        "mustInclude": list(brief.mustInclude),
        "allowedNumbers": list(brief.allowedNumbers),
        "forbidden": list(brief.forbidden),
        "length": {"min": brief.minCharacters, "max": brief.maxCharacters},
        "voiceReference": voiceReference,
    }


def reviewTemplate(cases: list[dict]) -> dict:
    return {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelReviewBatch",
        "suiteSha256": "<suiteSha256>",
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "evaluator": {
            "id": "<required>",
            "group": "targetReader",
            "protocolRevision": PANEL_PROTOCOL_REVISION,
        },
        "reviews": [
            {
                "caseId": panelCase["caseId"],
                "caseSha256": panelCase["caseSha256"],
                "contentChecks": {"left": "cannotJudge", "right": "cannotJudge"},
                "preferences": {dimension: "cannotJudge" for dimension in PANEL_DIMENSIONS},
                "reasons": {"content": "<required>"} | {dimension: "<required>" for dimension in PANEL_DIMENSIONS},
            }
            for panelCase in cases
        ],
    }


def desiredCandidateLeft(index: int, total: int, seed: int) -> bool:
    first = int(sha256(f"panel-order:{seed}:{total}".encode()).hexdigest(), 16) % 2 == 1
    return first if index % 2 == 0 else not first


def seedForSide(trial: WritingTrial, start: int, wantedLeft: bool) -> int:
    for candidateSeed in range(start, start + 10000):
        if candidateIsLeft(trial, candidateSeed) == wantedLeft:
            return candidateSeed
    raise RuntimeError("원하는 블라인드 좌우 seed를 찾지 못했다")


def preparePanelSuite(
    trials: list[WritingTrial | dict],
    suiteId: str,
    seed: int,
    voiceReferences: dict[str, dict | None] | None = None,
) -> dict:
    """같은 전략의 trial을 평가 맥락이 있는 사람용 블라인드 suite로 만든다."""
    suiteId = checkedString(suiteId, "suiteId")
    seed = checkedInteger(seed, "seed")
    parsed = [item if isinstance(item, WritingTrial) else WritingTrial.fromMapping(item) for item in trials]
    if not parsed:
        raise ValueError("panel suite에는 writing trial이 하나 이상 필요하다")
    identifiers = [trial.id for trial in parsed]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("panel suite의 trial id가 겹친다")
    candidateStrategies = {trial.candidate.strategyId for trial in parsed}
    if len(candidateStrategies) != 1:
        raise ValueError("panel suite에는 같은 candidate strategy trial만 넣는다")
    voiceReferences = voiceReferences or {}
    unknownVoice = sorted(set(voiceReferences) - set(identifiers))
    if unknownVoice:
        raise ValueError(f"voiceReference가 모르는 trial을 가리킨다: {', '.join(unknownVoice)}")

    eligibleById = {
        trial.id: prepareBlind(trial, 0, Config(preset=trial.brief.preset))["eligibleForPreference"] for trial in parsed
    }
    eligibleTotal = sum(eligibleById.values())
    eligibleIndex = 0
    cases = []
    excluded = []
    for index, trial in enumerate(parsed):
        if eligibleById[trial.id]:
            wantedLeft = desiredCandidateLeft(eligibleIndex, eligibleTotal, seed)
            caseSeed = seedForSide(trial, seed + index * 10007, wantedLeft)
            eligibleIndex += 1
        else:
            caseSeed = seed + index * 10007
        blind = prepareBlind(trial, caseSeed, Config(preset=trial.brief.preset))
        if not blind["eligibleForPreference"]:
            excluded.append(
                {
                    "caseId": trial.id,
                    "trialSha256": trial.digest,
                    "seed": caseSeed,
                    "safetyOutcome": blind["safetyOutcome"],
                    "sourceBlindSha256": blind["blindSha256"],
                }
            )
            continue
        voiceReference = checkedVoiceReference(voiceReferences.get(trial.id), f"voiceReferences.{trial.id}")
        panelCase = {
            "caseId": trial.id,
            "trialSha256": trial.digest,
            "seed": caseSeed,
            "sourceBlindSha256": blind["blindSha256"],
            "context": evaluationContext(trial, voiceReference),
            "comparison": deepcopy(blind["comparison"]),
        }
        panelCase["caseSha256"] = stableDigest(panelCase)
        cases.append(panelCase)

    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelSuite",
        "suiteId": suiteId,
        "seed": seed,
        "rubric": deepcopy(PANEL_RUBRIC),
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "protocol": {
            "revision": PANEL_PROTOCOL_REVISION,
            "minimumIndependentHumanReviews": 3,
            "identityHidden": ["strategy", "model", "author"],
            "assignment": "같은 evaluator는 case마다 한 좌우 순서만 보고 다른 evaluator의 판정을 보지 않는다",
        },
        "source": {
            "trials": len(parsed),
            "eligibleCases": len(cases),
            "excludedCases": len(excluded),
            "containsReferenceText": False,
        },
        "cases": cases,
        "excluded": excluded,
        "reviewTemplate": reviewTemplate(cases),
        "claimBoundary": (
            "이 suite는 자동 안전 계약을 통과한 글만 사람에게 보인다. 사람 합의 전에는 자연스러움이나 "
            "작법 전략의 향상을 주장하지 않는다"
        ),
    }
    payload["suiteSha256"] = suiteDigest(payload)
    payload["reviewTemplate"]["suiteSha256"] = payload["suiteSha256"]
    return payload


def checkedContext(data: object, where: str) -> dict:
    data = exactKeys(
        data,
        {
            "genre",
            "reader",
            "task",
            "facts",
            "mustInclude",
            "allowedNumbers",
            "forbidden",
            "length",
            "voiceReference",
        },
        where,
    )
    checkedString(data["genre"], f"{where}.genre")
    checkedString(data["reader"], f"{where}.reader")
    checkedString(data["task"], f"{where}.task")
    if not isinstance(data["facts"], list) or not data["facts"]:
        raise ValueError(f"{where}.facts 는 비지 않은 배열이다")
    for index, fact in enumerate(data["facts"], start=1):
        exactKeys(fact, {"id", "statement"}, f"{where}.facts {index}번째")
        checkedString(fact["id"], f"{where}.facts {index}번째 id")
        checkedString(fact["statement"], f"{where}.facts {index}번째 statement")
    for name in ("mustInclude", "allowedNumbers", "forbidden"):
        if not isinstance(data[name], list):
            raise ValueError(f"{where}.{name} 는 배열이다")
        for index, value in enumerate(data[name], start=1):
            checkedString(value, f"{where}.{name} {index}번째")
    length = exactKeys(data["length"], {"min", "max"}, f"{where}.length")
    minimum = checkedInteger(length["min"], f"{where}.length.min", 1)
    maximum = checkedInteger(length["max"], f"{where}.length.max", 1)
    if maximum < minimum:
        raise ValueError(f"{where}.length 는 min 이하가 max다")
    checkedVoiceReference(data["voiceReference"], f"{where}.voiceReference")
    return data


def checkedPanelSuite(data: object) -> dict:
    data = exactKeys(
        data,
        {
            "version",
            "kind",
            "suiteId",
            "seed",
            "rubric",
            "rubricSha256",
            "protocol",
            "source",
            "cases",
            "excluded",
            "reviewTemplate",
            "claimBoundary",
            "suiteSha256",
        },
        "panel suite",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != "hanlint.panelSuite":
        raise ValueError("panel suite의 version 또는 kind가 다르다")
    checkedString(data["suiteId"], "panel suite suiteId")
    checkedInteger(data["seed"], "panel suite seed")
    if data["rubric"] != PANEL_RUBRIC or data["rubricSha256"] != PANEL_RUBRIC_SHA256:
        raise ValueError("panel suite의 rubric이 고정 판과 다르다")
    protocol = exactKeys(
        data["protocol"],
        {"revision", "minimumIndependentHumanReviews", "identityHidden", "assignment"},
        "panel suite protocol",
    )
    if protocol["revision"] != PANEL_PROTOCOL_REVISION or protocol["minimumIndependentHumanReviews"] != 3:
        raise ValueError("panel suite의 protocol 판 또는 최소 검토자 수가 다르다")
    if protocol["identityHidden"] != ["strategy", "model", "author"]:
        raise ValueError("panel suite가 가리는 정체성 목록이 다르다")
    checkedString(protocol["assignment"], "panel suite protocol.assignment")
    exactKeys(
        data["source"],
        {"trials", "eligibleCases", "excludedCases", "containsReferenceText"},
        "panel suite source",
    )
    for name in ("trials", "eligibleCases", "excludedCases"):
        checkedInteger(data["source"][name], f"panel suite source.{name}")
    if data["source"]["containsReferenceText"] is not False:
        raise ValueError("panel suite는 참조 말뭉치 원문을 담지 않는다")
    if not isinstance(data["cases"], list) or not isinstance(data["excluded"], list):
        raise ValueError("panel suite의 cases와 excluded는 배열이다")
    identifiers = []
    for index, item in enumerate(data["cases"], start=1):
        where = f"panel suite cases {index}번째"
        item = exactKeys(
            item,
            {"caseId", "trialSha256", "seed", "sourceBlindSha256", "context", "comparison", "caseSha256"},
            where,
        )
        identifiers.append(checkedString(item["caseId"], f"{where}.caseId"))
        checkedSha(item["trialSha256"], f"{where}.trialSha256")
        checkedInteger(item["seed"], f"{where}.seed")
        checkedSha(item["sourceBlindSha256"], f"{where}.sourceBlindSha256")
        checkedContext(item["context"], f"{where}.context")
        comparison = exactKeys(item["comparison"], {"left", "right"}, f"{where}.comparison")
        checkedText(comparison["left"], f"{where}.comparison.left")
        checkedText(comparison["right"], f"{where}.comparison.right")
        if comparison["left"] == comparison["right"]:
            raise ValueError(f"{where}의 좌우 글이 같다")
        caseSha = checkedSha(item["caseSha256"], f"{where}.caseSha256")
        if caseSha != digestWithout(item, "caseSha256"):
            raise ValueError(f"{where}.caseSha256가 내용과 다르다")
    for index, item in enumerate(data["excluded"], start=1):
        where = f"panel suite excluded {index}번째"
        exactKeys(item, {"caseId", "trialSha256", "seed", "safetyOutcome", "sourceBlindSha256"}, where)
        identifiers.append(checkedString(item["caseId"], f"{where}.caseId"))
        checkedSha(item["trialSha256"], f"{where}.trialSha256")
        checkedInteger(item["seed"], f"{where}.seed")
        checkedString(item["safetyOutcome"], f"{where}.safetyOutcome")
        checkedSha(item["sourceBlindSha256"], f"{where}.sourceBlindSha256")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("panel suite의 caseId가 겹친다")
    if data["source"]["trials"] != len(identifiers):
        raise ValueError("panel suite의 source.trials가 실제 case 수와 다르다")
    if data["source"]["eligibleCases"] != len(data["cases"]) or data["source"]["excludedCases"] != len(data["excluded"]):
        raise ValueError("panel suite의 source case 수가 실제와 다르다")
    if data["reviewTemplate"] != (reviewTemplate(data["cases"]) | {"suiteSha256": data["suiteSha256"]}):
        raise ValueError("panel suite의 reviewTemplate이 다르다")
    checkedString(data["claimBoundary"], "panel suite claimBoundary")
    suiteSha = checkedSha(data["suiteSha256"], "panel suite suiteSha256")
    if suiteSha != suiteDigest(data):
        raise ValueError("panel suite의 suiteSha256가 내용과 다르다")
    return data


def checkedReason(value: object, where: str) -> str:
    value = checkedString(value, where)
    if value == "<required>":
        raise ValueError(f"{where}의 <required>를 실제 근거로 바꾼다")
    return value


def recordPanelReviewBatch(suite: dict, data: object) -> dict:
    """평가자 한 명의 독립 검토 묶음을 검증하고 해시로 잠근다."""
    suite = checkedPanelSuite(suite)
    data = exactKeys(
        data,
        {"version", "kind", "suiteSha256", "rubricSha256", "evaluator", "reviews"},
        "panel review batch",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != "hanlint.panelReviewBatch":
        raise ValueError("panel review batch의 version 또는 kind가 다르다")
    if data["suiteSha256"] != suite["suiteSha256"] or data["rubricSha256"] != PANEL_RUBRIC_SHA256:
        raise ValueError("panel review batch의 suite 또는 rubric SHA256가 다르다")
    evaluator = exactKeys(data["evaluator"], {"id", "group", "protocolRevision"}, "panel review evaluator")
    evaluatorId = checkedString(evaluator["id"], "panel review evaluator.id")
    if evaluatorId == "<required>":
        raise ValueError("panel review evaluator.id의 <required>를 실제 가명으로 바꾼다")
    if evaluator["group"] not in EVALUATOR_GROUPS:
        raise ValueError(f"panel review evaluator.group은 {', '.join(EVALUATOR_GROUPS)} 가운데 하나다")
    if evaluator["protocolRevision"] != PANEL_PROTOCOL_REVISION:
        raise ValueError("panel review evaluator.protocolRevision이 다르다")
    if not isinstance(data["reviews"], list) or not data["reviews"]:
        raise ValueError("panel review batch의 reviews는 비지 않은 배열이다")
    cases = {item["caseId"]: item for item in suite["cases"]}
    normalized = []
    seen = set()
    for index, review in enumerate(data["reviews"], start=1):
        where = f"panel review {index}번째"
        review = exactKeys(
            review,
            {"caseId", "caseSha256", "contentChecks", "preferences", "reasons"},
            where,
        )
        caseId = checkedString(review["caseId"], f"{where}.caseId")
        if caseId not in cases:
            raise ValueError(f"{where}가 suite에 없는 case를 가리킨다: {caseId}")
        if caseId in seen:
            raise ValueError(f"같은 evaluator가 case를 두 번 검토했다: {caseId}")
        seen.add(caseId)
        if review["caseSha256"] != cases[caseId]["caseSha256"]:
            raise ValueError(f"{where}.caseSha256가 suite와 다르다")
        content = exactKeys(review["contentChecks"], {"left", "right"}, f"{where}.contentChecks")
        if any(choice not in CONTENT_CHOICES for choice in content.values()):
            raise ValueError(f"{where}.contentChecks의 선택이 잘못됐다")
        preferences = exactKeys(review["preferences"], set(PANEL_DIMENSIONS), f"{where}.preferences")
        if any(choice not in PANEL_CHOICES for choice in preferences.values()):
            raise ValueError(f"{where}.preferences의 선택이 잘못됐다")
        bothPass = all(choice == "pass" for choice in content.values())
        if not bothPass and any(choice != "cannotJudge" for choice in preferences.values()):
            raise ValueError(f"{where}는 한쪽 content가 pass가 아니므로 모든 선호를 cannotJudge로 둔다")
        hasVoice = cases[caseId]["context"]["voiceReference"] is not None
        if not hasVoice and preferences["voice"] != "cannotJudge":
            raise ValueError(f"{where}는 voiceReference가 없어 voice를 cannotJudge로 둔다")
        reasons = exactKeys(review["reasons"], {"content", *PANEL_DIMENSIONS}, f"{where}.reasons")
        normalized.append(
            {
                "caseId": caseId,
                "caseSha256": cases[caseId]["caseSha256"],
                "contentChecks": {side: content[side] for side in ("left", "right")},
                "preferences": {dimension: preferences[dimension] for dimension in PANEL_DIMENSIONS},
                "reasons": {
                    name: checkedReason(reasons[name], f"{where}.reasons.{name}") for name in ("content", *PANEL_DIMENSIONS)
                },
            }
        )
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.recordedPanelReviewBatch",
        "suiteSha256": suite["suiteSha256"],
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "evaluator": {
            "id": evaluatorId,
            "group": evaluator["group"],
            "protocolRevision": PANEL_PROTOCOL_REVISION,
        },
        "reviews": normalized,
        "meaning": "한 평가자의 독립 선택이다. 패널 합의나 글 품질 판정이 아니다",
    }
    payload["batchSha256"] = digestWithout(payload, "batchSha256")
    return payload


def checkedRecordedBatch(suite: dict, data: object) -> dict:
    data = exactKeys(
        data,
        {
            "version",
            "kind",
            "suiteSha256",
            "rubricSha256",
            "evaluator",
            "reviews",
            "meaning",
            "batchSha256",
        },
        "recorded panel review batch",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != "hanlint.recordedPanelReviewBatch":
        raise ValueError("recorded panel review batch의 version 또는 kind가 다르다")
    base = {
        "version": data["version"],
        "kind": "hanlint.panelReviewBatch",
        "suiteSha256": data["suiteSha256"],
        "rubricSha256": data["rubricSha256"],
        "evaluator": data["evaluator"],
        "reviews": data["reviews"],
    }
    normalized = recordPanelReviewBatch(suite, base)
    if data != normalized:
        raise ValueError("recorded panel review batch가 원본 계약에서 만든 결과와 다르다")
    return data


def strictConsensus(values: list[str], valid: tuple[str, ...], minimum: int) -> tuple[str, dict[str, int], int]:
    counts = {choice: values.count(choice) for choice in (*valid, "cannotJudge")}
    answered = sum(counts[choice] for choice in valid)
    if answered < minimum:
        return "noConsensus", counts, answered
    winner = max(valid, key=lambda choice: counts[choice])
    if counts[winner] * 2 <= answered:
        return "noConsensus", counts, answered
    return winner, counts, answered


def nominalAlpha(units: list[list[str]], categories: tuple[str, ...]) -> dict:
    coincidence: Counter[tuple[str, str]] = Counter()
    marginals: Counter[str] = Counter()
    pairableUnits = 0
    ratings = 0
    for values in units:
        selected = [value for value in values if value in categories]
        if len(selected) < 2:
            continue
        pairableUnits += 1
        ratings += len(selected)
        for leftIndex, left in enumerate(selected):
            marginals[left] += 1
            for rightIndex, right in enumerate(selected):
                if leftIndex != rightIndex:
                    coincidence[(left, right)] += 1 / (len(selected) - 1)
    if ratings < 2:
        return {"alpha": None, "pairableUnits": pairableUnits, "ratings": ratings}
    observed = sum(value for (left, right), value in coincidence.items() if left != right) / ratings
    expectedNumerator = ratings * ratings - sum(count * count for count in marginals.values())
    expected = expectedNumerator / (ratings * (ratings - 1))
    alpha = None if expected == 0 else round(1 - observed / expected, 6)
    return {"alpha": alpha, "pairableUnits": pairableUnits, "ratings": ratings}


def adjudicatePanel(suite: dict, batches: list[dict]) -> dict:
    """세 명 이상 사람 검토의 엄격 다수와 명목 Krippendorff alpha를 계산한다."""
    suite = checkedPanelSuite(suite)
    if not batches:
        raise ValueError("panel adjudication에는 recorded review batch가 하나 이상 필요하다")
    checked = [checkedRecordedBatch(suite, batch) for batch in batches]
    evaluatorIds = [batch["evaluator"]["id"] for batch in checked]
    if len(set(evaluatorIds)) != len(evaluatorIds):
        raise ValueError("panel adjudication의 evaluator id가 겹친다")
    minimum = suite["protocol"]["minimumIndependentHumanReviews"]
    if len(evaluatorIds) < minimum:
        raise ValueError(f"panel adjudication에는 독립 evaluator가 최소 {minimum}명 필요하다")
    reviewsByCase: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for batch in checked:
        for review in batch["reviews"]:
            reviewsByCase[review["caseId"]].append((batch["evaluator"], review))
    cases = []
    for panelCase in suite["cases"]:
        rows = reviewsByCase.get(panelCase["caseId"], [])
        contentConsensus = {}
        contentCounts = {}
        contentAnswered = {}
        for side in ("left", "right"):
            consensus, counts, answered = strictConsensus(
                [review["contentChecks"][side] for _, review in rows],
                ("pass", "fail"),
                minimum,
            )
            contentConsensus[side] = consensus
            contentCounts[side] = counts
            contentAnswered[side] = answered
        preferenceConsensus = {}
        preferenceCounts = {}
        preferenceAnswered = {}
        contentEligible = all(contentConsensus[side] == "pass" for side in ("left", "right"))
        for dimension in PANEL_DIMENSIONS:
            consensus, counts, answered = strictConsensus(
                [review["preferences"][dimension] for _, review in rows],
                ("left", "right", "tie"),
                minimum,
            )
            if not contentEligible:
                consensus = "ineligible"
            preferenceConsensus[dimension] = consensus
            preferenceCounts[dimension] = counts
            preferenceAnswered[dimension] = answered
        cases.append(
            {
                "caseId": panelCase["caseId"],
                "caseSha256": panelCase["caseSha256"],
                "genre": panelCase["context"]["genre"],
                "humanReviews": len(rows),
                "evaluatorGroups": dict(sorted(Counter(evaluator["group"] for evaluator, _ in rows).items())),
                "content": {
                    "consensus": contentConsensus,
                    "counts": contentCounts,
                    "answered": contentAnswered,
                },
                "preferences": {
                    "consensus": preferenceConsensus,
                    "counts": preferenceCounts,
                    "answered": preferenceAnswered,
                },
            }
        )
    contentUnits = []
    for panelCase in suite["cases"]:
        rows = reviewsByCase.get(panelCase["caseId"], [])
        for side in ("left", "right"):
            contentUnits.append([review["contentChecks"][side] for _, review in rows])
    preferenceAgreement = {}
    for dimension in PANEL_DIMENSIONS:
        units = [
            [review["preferences"][dimension] for _, review in reviewsByCase.get(panelCase["caseId"], [])]
            for panelCase in suite["cases"]
        ]
        preferenceAgreement[dimension] = nominalAlpha(units, ("left", "right", "tie"))
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelAdjudication",
        "suiteId": suite["suiteId"],
        "suiteSha256": suite["suiteSha256"],
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "minimumIndependentHumanReviews": minimum,
        "evaluators": len(set(evaluatorIds)),
        "reviewBatches": [batch["batchSha256"] for batch in checked],
        "agreement": {
            "method": "KrippendorffAlphaNominal",
            "content": nominalAlpha(contentUnits, ("pass", "fail")),
            "preferences": preferenceAgreement,
        },
        "cases": cases,
        "claimBoundary": (
            "엄격 다수와 평가자 간 합의는 이 사람 패널과 이 글 쌍의 결과다. 낮은 alpha를 평균으로 감추거나 "
            "다른 장르와 독자의 보편적 품질로 넓히지 않는다"
        ),
    }
    payload["adjudicationSha256"] = digestWithout(payload, "adjudicationSha256")
    return payload


def checkedAdjudication(suite: dict, data: object) -> dict:
    data = exactKeys(
        data,
        {
            "version",
            "kind",
            "suiteId",
            "suiteSha256",
            "rubricSha256",
            "minimumIndependentHumanReviews",
            "evaluators",
            "reviewBatches",
            "agreement",
            "cases",
            "claimBoundary",
            "adjudicationSha256",
        },
        "panel adjudication",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != "hanlint.panelAdjudication":
        raise ValueError("panel adjudication의 version 또는 kind가 다르다")
    if data["suiteId"] != suite["suiteId"] or data["suiteSha256"] != suite["suiteSha256"]:
        raise ValueError("panel adjudication의 suite가 다르다")
    if data["rubricSha256"] != PANEL_RUBRIC_SHA256:
        raise ValueError("panel adjudication의 rubric이 다르다")
    minimum = checkedInteger(
        data["minimumIndependentHumanReviews"],
        "panel adjudication minimumIndependentHumanReviews",
        1,
    )
    if minimum != suite["protocol"]["minimumIndependentHumanReviews"]:
        raise ValueError("panel adjudication의 최소 독립 검토자 수가 suite와 다르다")
    evaluators = checkedInteger(data["evaluators"], "panel adjudication evaluators", minimum)
    if not isinstance(data["reviewBatches"], list) or len(data["reviewBatches"]) != evaluators:
        raise ValueError("panel adjudication reviewBatches 수가 evaluator 수와 다르다")
    reviewBatches = [
        checkedSha(value, f"panel adjudication reviewBatches {index}번째")
        for index, value in enumerate(data["reviewBatches"], start=1)
    ]
    if len(set(reviewBatches)) != len(reviewBatches):
        raise ValueError("panel adjudication reviewBatches가 겹친다")
    agreement = exactKeys(data["agreement"], {"method", "content", "preferences"}, "panel adjudication agreement")
    if agreement["method"] != "KrippendorffAlphaNominal":
        raise ValueError("panel adjudication agreement method가 다르다")
    checkedAgreementMetric(agreement["content"], "panel adjudication agreement.content")
    preferencesAgreement = exactKeys(
        agreement["preferences"],
        set(PANEL_DIMENSIONS),
        "panel adjudication agreement.preferences",
    )
    for dimension in PANEL_DIMENSIONS:
        checkedAgreementMetric(
            preferencesAgreement[dimension],
            f"panel adjudication agreement.preferences.{dimension}",
        )
    checkedSha(data["adjudicationSha256"], "panel adjudication adjudicationSha256")
    if data["adjudicationSha256"] != digestWithout(data, "adjudicationSha256"):
        raise ValueError("panel adjudication의 digest가 다르다")
    expectedCaseIds = [item["caseId"] for item in suite["cases"]]
    if [item.get("caseId") for item in data["cases"]] != expectedCaseIds:
        raise ValueError("panel adjudication의 case 순서가 suite와 다르다")
    suiteCases = {item["caseId"]: item for item in suite["cases"]}
    for index, item in enumerate(data["cases"], start=1):
        where = f"panel adjudication cases {index}번째"
        item = exactKeys(
            item,
            {
                "caseId",
                "caseSha256",
                "genre",
                "humanReviews",
                "evaluatorGroups",
                "content",
                "preferences",
            },
            where,
        )
        panelCase = suiteCases[item["caseId"]]
        if item["caseSha256"] != panelCase["caseSha256"] or item["genre"] != panelCase["context"]["genre"]:
            raise ValueError(f"{where}의 case SHA256 또는 genre가 suite와 다르다")
        humanReviews = checkedInteger(item["humanReviews"], f"{where}.humanReviews")
        if humanReviews > evaluators:
            raise ValueError(f"{where}.humanReviews가 전체 evaluator보다 많다")
        if not isinstance(item["evaluatorGroups"], dict) or any(
            group not in EVALUATOR_GROUPS for group in item["evaluatorGroups"]
        ):
            raise ValueError(f"{where}.evaluatorGroups에 모르는 집단이 있다")
        groupCounts = [
            checkedInteger(value, f"{where}.evaluatorGroups.{group}", 1) for group, value in item["evaluatorGroups"].items()
        ]
        if sum(groupCounts) != humanReviews:
            raise ValueError(f"{where}.evaluatorGroups 합이 humanReviews와 다르다")
        content = exactKeys(item["content"], {"consensus", "counts", "answered"}, f"{where}.content")
        contentConsensus = exactKeys(content["consensus"], {"left", "right"}, f"{where}.content.consensus")
        contentCounts = exactKeys(content["counts"], {"left", "right"}, f"{where}.content.counts")
        contentAnswered = exactKeys(content["answered"], {"left", "right"}, f"{where}.content.answered")
        for side in ("left", "right"):
            checkedConsensusAggregate(
                contentConsensus[side],
                contentCounts[side],
                contentAnswered[side],
                ("pass", "fail"),
                humanReviews,
                minimum,
                f"{where}.content.{side}",
            )
        preferences = exactKeys(
            item["preferences"],
            {"consensus", "counts", "answered"},
            f"{where}.preferences",
        )
        preferenceConsensus = exactKeys(
            preferences["consensus"],
            set(PANEL_DIMENSIONS),
            f"{where}.preferences.consensus",
        )
        preferenceCounts = exactKeys(
            preferences["counts"],
            set(PANEL_DIMENSIONS),
            f"{where}.preferences.counts",
        )
        preferenceAnswered = exactKeys(
            preferences["answered"],
            set(PANEL_DIMENSIONS),
            f"{where}.preferences.answered",
        )
        contentEligible = all(contentConsensus[side] == "pass" for side in ("left", "right"))
        for dimension in PANEL_DIMENSIONS:
            expectedConsensus = checkedConsensusAggregate(
                preferenceConsensus[dimension] if contentEligible else None,
                preferenceCounts[dimension],
                preferenceAnswered[dimension],
                ("left", "right", "tie"),
                humanReviews,
                minimum,
                f"{where}.preferences.{dimension}",
            )
            actualConsensus = preferenceConsensus[dimension]
            if (contentEligible and actualConsensus != expectedConsensus) or (
                not contentEligible and actualConsensus != "ineligible"
            ):
                raise ValueError(f"{where}.preferences.{dimension} consensus가 content 계약과 다르다")
    checkedString(data["claimBoundary"], "panel adjudication claimBoundary")
    return data


def checkedAgreementMetric(data: object, where: str) -> dict:
    data = exactKeys(data, {"alpha", "pairableUnits", "ratings"}, where)
    alpha = data["alpha"]
    if alpha is not None and (
        isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or float(alpha) > 1 or float(alpha) != float(alpha)
    ):
        raise ValueError(f"{where}.alpha는 1 이하 숫자 또는 null이다")
    checkedInteger(data["pairableUnits"], f"{where}.pairableUnits")
    checkedInteger(data["ratings"], f"{where}.ratings")
    return data


def checkedConsensusAggregate(
    consensus: object,
    counts: object,
    answered: object,
    valid: tuple[str, ...],
    humanReviews: int,
    minimum: int,
    where: str,
) -> str:
    counts = exactKeys(counts, {*valid, "cannotJudge"}, f"{where}.counts")
    normalizedCounts = {choice: checkedInteger(counts[choice], f"{where}.counts.{choice}") for choice in (*valid, "cannotJudge")}
    if sum(normalizedCounts.values()) != humanReviews:
        raise ValueError(f"{where}.counts 합이 humanReviews와 다르다")
    answered = checkedInteger(answered, f"{where}.answered")
    if answered != sum(normalizedCounts[choice] for choice in valid):
        raise ValueError(f"{where}.answered가 counts와 다르다")
    values = [choice for choice in (*valid, "cannotJudge") for _ in range(normalizedCounts[choice])]
    expected, _, _ = strictConsensus(values, valid, minimum)
    if consensus is not None and consensus != expected:
        raise ValueError(f"{where}.consensus가 counts의 엄격 다수와 다르다")
    return expected


def bootstrapMean(values: list[float], seedKey: str, iterations: int = 5000) -> dict | None:
    if not values:
        return None
    random = Random(int(sha256(seedKey.encode()).hexdigest(), 16))
    means = []
    for _ in range(iterations):
        means.append(sum(values[random.randrange(len(values))] for _ in values) / len(values))
    means.sort()
    low = means[int(0.025 * (iterations - 1))]
    high = means[int(0.975 * (iterations - 1))]
    return {"low": round(low, 6), "high": round(high, 6), "iterations": iterations}


def preferenceSummary(mapped: list[dict], dimension: str, seedKey: str) -> dict:
    choices = [item["preferences"].get(dimension) for item in mapped]
    selected = [choice for choice in choices if choice in ("candidate", "baseline", "tie")]
    values = [1.0 if choice == "candidate" else 0.0 if choice == "baseline" else 0.5 for choice in selected]
    return {
        "eligibleCases": len(selected),
        "candidate": selected.count("candidate"),
        "baseline": selected.count("baseline"),
        "tie": selected.count("tie"),
        "noConsensus": len(choices) - len(selected),
        "candidatePreferenceShare": round(sum(values) / len(values), 6) if values else None,
        "candidatePreferenceShareCi95": bootstrapMean(values, seedKey),
    }


def revealPanel(trials: list[WritingTrial | dict], suite: dict, adjudication: dict) -> dict:
    """사람 합의 좌우를 strategy 이름으로 되돌리고 case bootstrap 구간을 낸다."""
    suite = checkedPanelSuite(suite)
    adjudication = checkedAdjudication(suite, adjudication)
    parsed = [item if isinstance(item, WritingTrial) else WritingTrial.fromMapping(item) for item in trials]
    byId = {trial.id: trial for trial in parsed}
    if len(byId) != len(parsed):
        raise ValueError("panel reveal의 trial id가 겹친다")
    expectedIds = {item["caseId"] for item in suite["cases"]} | {item["caseId"] for item in suite["excluded"]}
    if set(byId) != expectedIds:
        raise ValueError("panel reveal의 trial 집합이 suite와 다르다")
    candidateStrategies = {trial.candidate.strategyId for trial in parsed}
    if len(candidateStrategies) != 1:
        raise ValueError("panel reveal에는 같은 candidate strategy만 넣는다")
    adjudicated = {item["caseId"]: item for item in adjudication["cases"]}
    mapped = []
    for panelCase in suite["cases"]:
        trial = byId[panelCase["caseId"]]
        blind = prepareBlind(trial, panelCase["seed"], Config(preset=trial.brief.preset))
        if blind["blindSha256"] != panelCase["sourceBlindSha256"]:
            raise ValueError(f"panel reveal의 trial이 suite case와 다르다: {trial.id}")
        candidateLeft = candidateIsLeft(trial, panelCase["seed"])

        def mapPreference(choice: str, candidateOnLeft: bool = candidateLeft) -> str:
            if choice == "tie":
                return "tie"
            if choice not in ("left", "right"):
                return choice
            return "candidate" if (choice == "left") == candidateOnLeft else "baseline"

        source = adjudicated[trial.id]
        mapped.append(
            {
                "caseId": trial.id,
                "genre": trial.brief.preset,
                "humanReviews": source["humanReviews"],
                "content": {
                    "candidate": source["content"]["consensus"]["left" if candidateLeft else "right"],
                    "baseline": source["content"]["consensus"]["right" if candidateLeft else "left"],
                },
                "preferences": {
                    dimension: mapPreference(source["preferences"]["consensus"][dimension]) for dimension in PANEL_DIMENSIONS
                },
            }
        )
    dimensions = {
        dimension: preferenceSummary(mapped, dimension, f"{adjudication['adjudicationSha256']}:{dimension}")
        for dimension in PANEL_DIMENSIONS
    }
    byGenre = {}
    for genre in sorted({item["genre"] for item in mapped}):
        selected = [item for item in mapped if item["genre"] == genre]
        byGenre[genre] = {
            dimension: preferenceSummary(
                selected,
                dimension,
                f"{adjudication['adjudicationSha256']}:{genre}:{dimension}",
            )
            for dimension in PANEL_DIMENSIONS
        }
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelStrategyResult",
        "suiteId": suite["suiteId"],
        "suiteSha256": suite["suiteSha256"],
        "adjudicationSha256": adjudication["adjudicationSha256"],
        "baselineStrategyId": "plainBrief",
        "candidateStrategyId": next(iter(candidateStrategies)),
        "automaticSafety": {
            "eligible": len(suite["cases"]),
            "excluded": len(suite["excluded"]),
            "outcomes": dict(sorted(Counter(item["safetyOutcome"] for item in suite["excluded"]).items())),
        },
        "agreement": adjudication["agreement"],
        "dimensions": dimensions,
        "byGenre": byGenre,
        "cases": mapped,
        "claimBoundary": (
            "candidatePreferenceShare는 무승부를 0.5로 센 이 suite의 사람 패널 기술값이다. "
            "30개 미만 case와 낮은 "
            "alpha에서는 탐색 결과이며 제품 점수나 일반 품질 향상이 아니다"
        ),
    }
    payload["resultSha256"] = digestWithout(payload, "resultSha256")
    return payload


def preparePanelJudgeCases(suite: dict) -> dict:
    """자동 심사기의 위치 편향을 재도록 모든 사람 case를 양쪽 순서로 낸다."""
    suite = checkedPanelSuite(suite)
    presentations = []
    for panelCase in suite["cases"]:
        for order in ("forward", "reversed"):
            comparison = deepcopy(panelCase["comparison"])
            if order == "reversed":
                comparison = {"left": comparison["right"], "right": comparison["left"]}
            presentation = {
                "presentationId": f"{panelCase['caseId']}:{order}",
                "caseId": panelCase["caseId"],
                "caseSha256": panelCase["caseSha256"],
                "order": order,
                "context": deepcopy(panelCase["context"]),
                "comparison": comparison,
            }
            presentation["presentationSha256"] = stableDigest(presentation)
            presentations.append(presentation)
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelJudgeCases",
        "suiteId": suite["suiteId"],
        "suiteSha256": suite["suiteSha256"],
        "rubric": deepcopy(PANEL_RUBRIC),
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "labels": {
            "content": list(JUDGE_CONTENT_CHOICES),
            "preference": list(JUDGE_CHOICES),
        },
        "presentations": presentations,
        "instruction": (
            "evaluator에는 context와 comparison만 주고 각 presentation을 독립적으로 판정한다. presentationId, "
            "caseId, order와 사람 합의는 주지 않는다. content 한쪽을 fail 또는 abstain으로 두면 네 preference를 "
            "모두 abstain으로 둔다"
        ),
        "claimBoundary": "자동 심사기 출력은 사람 선호가 아니며 양쪽 순서가 일치하는지와 사람 합의 일치도를 따로 잰다",
    }
    payload["judgeCasesSha256"] = digestWithout(payload, "judgeCasesSha256")
    return payload


def checkedJudgeCases(suite: dict, data: object) -> dict:
    expected = preparePanelJudgeCases(suite)
    if data != expected:
        raise ValueError("panel judge cases가 suite에서 만든 고정 결과와 다르다")
    return data


def checkedJudgeDecision(data: object, labels: tuple[str, ...], where: str) -> dict:
    data = exactKeys(data, {"choice", "confidence"}, where)
    choice = data["choice"]
    if choice not in labels:
        raise ValueError(f"{where}.choice가 허용 label이 아니다")
    confidence = checkedConfidence(data["confidence"], f"{where}.confidence", choice == "abstain")
    return {"choice": choice, "confidence": confidence}


def checkedJudgePredictions(judgeCases: dict, data: object) -> dict:
    data = exactKeys(
        data,
        {
            "version",
            "kind",
            "judgeCasesSha256",
            "evaluatorId",
            "evaluatorRevision",
            "promptSha256",
            "predictions",
        },
        "panel judge predictions",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != "hanlint.panelJudgePredictions":
        raise ValueError("panel judge predictions의 version 또는 kind가 다르다")
    if data["judgeCasesSha256"] != judgeCases["judgeCasesSha256"]:
        raise ValueError("panel judge predictions의 judgeCasesSha256가 다르다")
    checkedString(data["evaluatorId"], "panel judge predictions evaluatorId")
    revision = checkedSha(data["evaluatorRevision"], "panel judge predictions evaluatorRevision")
    if revision in {"0" * 64, "f" * 64}:
        raise ValueError("panel judge predictions evaluatorRevision은 실제 고정 모델 digest다")
    checkedSha(data["promptSha256"], "panel judge predictions promptSha256")
    if not isinstance(data["predictions"], list):
        raise ValueError("panel judge predictions predictions는 배열이다")
    expected = {item["presentationId"]: item for item in judgeCases["presentations"]}
    normalized = []
    seen = set()
    for index, prediction in enumerate(data["predictions"], start=1):
        where = f"panel judge prediction {index}번째"
        prediction = exactKeys(
            prediction,
            {"presentationId", "presentationSha256", "contentChecks", "preferences"},
            where,
        )
        presentationId = checkedString(prediction["presentationId"], f"{where}.presentationId")
        if presentationId not in expected:
            raise ValueError(f"{where}가 모르는 presentation을 가리킨다")
        if presentationId in seen:
            raise ValueError(f"panel judge prediction의 presentationId가 겹친다: {presentationId}")
        seen.add(presentationId)
        if prediction["presentationSha256"] != expected[presentationId]["presentationSha256"]:
            raise ValueError(f"{where}.presentationSha256가 다르다")
        content = exactKeys(prediction["contentChecks"], {"left", "right"}, f"{where}.contentChecks")
        normalizedContent = {
            side: checkedJudgeDecision(
                content[side],
                JUDGE_CONTENT_CHOICES,
                f"{where}.contentChecks.{side}",
            )
            for side in ("left", "right")
        }
        preferences = exactKeys(prediction["preferences"], set(PANEL_DIMENSIONS), f"{where}.preferences")
        normalizedPreferences = {
            dimension: checkedJudgeDecision(
                preferences[dimension],
                JUDGE_CHOICES,
                f"{where}.preferences.{dimension}",
            )
            for dimension in PANEL_DIMENSIONS
        }
        if any(item["choice"] != "pass" for item in normalizedContent.values()) and any(
            item["choice"] != "abstain" for item in normalizedPreferences.values()
        ):
            raise ValueError(f"{where}는 content가 모두 pass가 아니므로 preference를 모두 abstain으로 둔다")
        if (
            expected[presentationId]["context"]["voiceReference"] is None
            and normalizedPreferences["voice"]["choice"] != "abstain"
        ):
            raise ValueError(f"{where}는 voiceReference가 없어 voice를 abstain으로 둔다")
        normalized.append(
            {
                "presentationId": presentationId,
                "presentationSha256": expected[presentationId]["presentationSha256"],
                "contentChecks": normalizedContent,
                "preferences": normalizedPreferences,
            }
        )
    if seen != set(expected):
        missing = sorted(set(expected) - seen)
        raise ValueError(f"panel judge predictions에 빠진 presentation이다: {', '.join(missing)}")
    return {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelJudgePredictions",
        "judgeCasesSha256": judgeCases["judgeCasesSha256"],
        "evaluatorId": data["evaluatorId"],
        "evaluatorRevision": revision,
        "promptSha256": data["promptSha256"],
        "predictions": normalized,
    }


def normalizedPairDecision(forward: dict, reversedItem: dict) -> tuple[str, float, bool]:
    leftChoice = forward["choice"]
    rightChoice = reversedItem["choice"]
    if rightChoice == "left":
        rightChoice = "right"
    elif rightChoice == "right":
        rightChoice = "left"
    answeredBoth = leftChoice != "abstain" and rightChoice != "abstain"
    consistent = answeredBoth and leftChoice == rightChoice
    if not consistent:
        return "abstain", 0.0, answeredBoth
    return leftChoice, min(forward["confidence"], reversedItem["confidence"]), True


def consistencyMetric(rows: list[tuple[str, bool]]) -> dict:
    comparable = sum(answeredBoth for _, answeredBoth in rows)
    consistent = sum(choice != "abstain" for choice, _ in rows)
    return {
        "pairs": len(rows),
        "comparable": comparable,
        "consistent": consistent,
        "consistency": round(consistent / comparable, 6) if comparable else None,
        "usableCoverage": round(consistent / len(rows), 6) if rows else 0.0,
        "decisions": dict(sorted(Counter(choice for choice, _ in rows).items())),
    }


def summarizePanelJudgeConsistency(suite: dict, judgeCases: dict, predictions: dict) -> dict:
    """사람 정답 없이 자동 심사기의 순서 일관성과 사용 가능 범위만 잰다."""
    suite = checkedPanelSuite(suite)
    judgeCases = checkedJudgeCases(suite, judgeCases)
    predictions = checkedJudgePredictions(judgeCases, predictions)
    byPresentation = {item["presentationId"]: item for item in predictions["predictions"]}
    contentRows: list[tuple[str, bool]] = []
    preferenceRows: dict[str, list[tuple[str, bool]]] = {dimension: [] for dimension in PANEL_DIMENSIONS}
    genreRows: dict[str, dict[str, list[tuple[str, bool]]]] = defaultdict(
        lambda: {dimension: [] for dimension in PANEL_DIMENSIONS}
    )
    for panelCase in suite["cases"]:
        caseId = panelCase["caseId"]
        genre = panelCase["context"]["genre"]
        forward = byPresentation[f"{caseId}:forward"]
        reversedItem = byPresentation[f"{caseId}:reversed"]
        for side in ("left", "right"):
            reverseSide = "right" if side == "left" else "left"
            choice, _, answeredBoth = normalizedPairDecision(
                forward["contentChecks"][side],
                reversedItem["contentChecks"][reverseSide],
            )
            contentRows.append((choice, answeredBoth))
        for dimension in PANEL_DIMENSIONS:
            choice, _, answeredBoth = normalizedPairDecision(
                forward["preferences"][dimension],
                reversedItem["preferences"][dimension],
            )
            row = (choice, answeredBoth)
            preferenceRows[dimension].append(row)
            genreRows[genre][dimension].append(row)
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelJudgeConsistency",
        "suiteId": suite["suiteId"],
        "suiteSha256": suite["suiteSha256"],
        "judgeCasesSha256": judgeCases["judgeCasesSha256"],
        "evaluatorId": predictions["evaluatorId"],
        "evaluatorRevision": predictions["evaluatorRevision"],
        "promptSha256": predictions["promptSha256"],
        "positionConsistency": {
            "content": consistencyMetric(contentRows),
            "preferences": {dimension: consistencyMetric(preferenceRows[dimension]) for dimension in PANEL_DIMENSIONS},
        },
        "byGenre": {
            genre: {dimension: consistencyMetric(rows[dimension]) for dimension in PANEL_DIMENSIONS}
            for genre, rows in sorted(genreRows.items())
        },
        "claimBoundary": (
            "사람 합의 없이 잰 자동 심사기의 좌우 순서 일관성과 사용 가능 범위다. 선호 정확도, 글의 품질이나 "
            "전략 향상을 뜻하지 않는다"
        ),
    }
    payload["consistencySha256"] = digestWithout(payload, "consistencySha256")
    return payload


def calibrationCurve(confidences: list[float], correct: list[int]) -> tuple[list[dict], float | None, float | None]:
    if not confidences:
        return [], None, None
    bins = []
    expectedError = 0.0
    for index in range(10):
        low = index / 10
        high = (index + 1) / 10
        positions = [
            position
            for position, confidence in enumerate(confidences)
            if low <= confidence <= high and (index == 9 or confidence < high)
        ]
        if not positions:
            continue
        meanConfidence = sum(confidences[position] for position in positions) / len(positions)
        accuracy = sum(correct[position] for position in positions) / len(positions)
        expectedError += len(positions) / len(confidences) * abs(meanConfidence - accuracy)
        bins.append(
            {
                "low": round(low, 1),
                "high": round(high, 1),
                "predictions": len(positions),
                "meanConfidence": round(meanConfidence, 6),
                "accuracy": round(accuracy, 6),
            }
        )
    brier = sum((confidence - outcome) ** 2 for confidence, outcome in zip(confidences, correct, strict=True)) / len(confidences)
    return bins, round(expectedError, 6), round(brier, 6)


def classificationMetrics(
    golds: list[str],
    predictions: list[str],
    confidences: list[float],
    labels: tuple[str, ...],
    seedKey: str,
) -> dict:
    total = len(golds)
    answeredPositions = [index for index, prediction in enumerate(predictions) if prediction != "abstain"]
    correct = [int(predictions[index] == golds[index]) for index in answeredPositions]
    answeredConfidences = [confidences[index] for index in answeredPositions]
    curve, calibrationError, brier = calibrationCurve(answeredConfidences, correct)
    confusion = {gold: {prediction: 0 for prediction in (*labels, "abstain")} for gold in labels}
    for gold, prediction in zip(golds, predictions, strict=True):
        confusion[gold][prediction] += 1
    perClass = {}
    for label in labels:
        truePositive = confusion[label][label]
        falsePositive = sum(confusion[gold][label] for gold in labels if gold != label)
        falseNegative = sum(confusion[label][prediction] for prediction in confusion[label] if prediction != label)
        precision = truePositive / (truePositive + falsePositive) if truePositive + falsePositive else 0.0
        recall = truePositive / (truePositive + falseNegative) if truePositive + falseNegative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        perClass[label] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": sum(gold == label for gold in golds),
        }
    selectedAccuracy = sum(correct) / len(correct) if correct else 0.0
    return {
        "total": total,
        "answered": len(answeredPositions),
        "abstained": total - len(answeredPositions),
        "coverage": round(len(answeredPositions) / total, 6) if total else 0.0,
        "selectedAccuracy": round(selectedAccuracy, 6),
        "selectedAccuracyCi95": bootstrapMean([float(value) for value in correct], seedKey),
        "macroF1": round(sum(item["f1"] for item in perClass.values()) / len(labels), 6),
        "confusionMatrix": confusion,
        "perClass": perClass,
        "calibration": {
            "expectedCalibrationError": calibrationError,
            "brierScore": brier,
            "bins": curve,
        },
    }


def evaluatePanelJudge(suite: dict, adjudication: dict, judgeCases: dict, predictions: dict) -> dict:
    """양쪽 순서가 같은 자동 판정만 사람 합의와 비교한다."""
    suite = checkedPanelSuite(suite)
    adjudication = checkedAdjudication(suite, adjudication)
    judgeCases = checkedJudgeCases(suite, judgeCases)
    predictions = checkedJudgePredictions(judgeCases, predictions)
    byPresentation = {item["presentationId"]: item for item in predictions["predictions"]}
    human = {item["caseId"]: item for item in adjudication["cases"]}
    position = {"content": {"comparable": 0, "consistent": 0}, "preferences": {}}
    preferenceRows: dict[str, list[dict]] = {dimension: [] for dimension in PANEL_DIMENSIONS}
    contentRows = []
    for panelCase in suite["cases"]:
        caseId = panelCase["caseId"]
        forward = byPresentation[f"{caseId}:forward"]
        reversedItem = byPresentation[f"{caseId}:reversed"]
        source = human[caseId]
        for side in ("left", "right"):
            reverseSide = "right" if side == "left" else "left"
            prediction, confidence, comparable = normalizedPairDecision(
                forward["contentChecks"][side],
                reversedItem["contentChecks"][reverseSide],
            )
            if comparable:
                position["content"]["comparable"] += 1
                if prediction != "abstain":
                    position["content"]["consistent"] += 1
            gold = source["content"]["consensus"][side]
            if gold in ("pass", "fail"):
                contentRows.append(
                    {
                        "caseId": caseId,
                        "genre": panelCase["context"]["genre"],
                        "gold": gold,
                        "prediction": prediction,
                        "confidence": confidence,
                    }
                )
        for dimension in PANEL_DIMENSIONS:
            prediction, confidence, comparable = normalizedPairDecision(
                forward["preferences"][dimension],
                reversedItem["preferences"][dimension],
            )
            position["preferences"].setdefault(dimension, {"comparable": 0, "consistent": 0})
            if comparable:
                position["preferences"][dimension]["comparable"] += 1
                if prediction != "abstain":
                    position["preferences"][dimension]["consistent"] += 1
            gold = source["preferences"]["consensus"][dimension]
            if gold in ("left", "right", "tie"):
                preferenceRows[dimension].append(
                    {
                        "caseId": caseId,
                        "genre": panelCase["context"]["genre"],
                        "gold": gold,
                        "prediction": prediction,
                        "confidence": confidence,
                    }
                )
    for values in (position["content"], *position["preferences"].values()):
        values["consistency"] = round(values["consistent"] / values["comparable"], 6) if values["comparable"] else None
    contentMetrics = classificationMetrics(
        [item["gold"] for item in contentRows],
        [item["prediction"] for item in contentRows],
        [item["confidence"] for item in contentRows],
        ("pass", "fail"),
        f"{predictions['evaluatorRevision']}:content",
    )
    preferenceMetrics = {}
    for dimension, rows in preferenceRows.items():
        preferenceMetrics[dimension] = classificationMetrics(
            [item["gold"] for item in rows],
            [item["prediction"] for item in rows],
            [item["confidence"] for item in rows],
            ("left", "right", "tie"),
            f"{predictions['evaluatorRevision']}:{dimension}",
        )
    genres = sorted({item["context"]["genre"] for item in suite["cases"]})
    byGenre = {}
    for genre in genres:
        byGenre[genre] = {}
        for dimension, rows in preferenceRows.items():
            selected = [item for item in rows if item["genre"] == genre]
            byGenre[genre][dimension] = classificationMetrics(
                [item["gold"] for item in selected],
                [item["prediction"] for item in selected],
                [item["confidence"] for item in selected],
                ("left", "right", "tie"),
                f"{predictions['evaluatorRevision']}:{genre}:{dimension}",
            )
    payload = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelJudgeEvaluation",
        "suiteId": suite["suiteId"],
        "suiteSha256": suite["suiteSha256"],
        "adjudicationSha256": adjudication["adjudicationSha256"],
        "judgeCasesSha256": judgeCases["judgeCasesSha256"],
        "evaluatorId": predictions["evaluatorId"],
        "evaluatorRevision": predictions["evaluatorRevision"],
        "promptSha256": predictions["promptSha256"],
        "positionConsistency": position,
        "content": contentMetrics,
        "preferences": preferenceMetrics,
        "byGenre": byGenre,
        "claimBoundary": (
            "자동 심사기의 양쪽 순서가 일치한 판정만 사람 패널 합의와 비교했다. 결과는 이 suite의 보정 "
            "지표이며 사람 선호, 사실의 진실이나 보편적 글 품질이 아니다"
        ),
    }
    payload["evaluationSha256"] = digestWithout(payload, "evaluationSha256")
    return payload


__all__ = [
    "CONTENT_CHOICES",
    "EVALUATOR_GROUPS",
    "PANEL_DIMENSIONS",
    "PANEL_PROTOCOL_REVISION",
    "PANEL_RUBRIC",
    "PANEL_RUBRIC_SHA256",
    "PANEL_VERSION",
    "adjudicatePanel",
    "checkedAdjudication",
    "checkedJudgePredictions",
    "checkedPanelSuite",
    "checkedPanelTrialSet",
    "evaluatePanelJudge",
    "loadPanelTrialSet",
    "preparePanelJudgeCases",
    "preparePanelSuite",
    "preparePanelTrialSet",
    "recordPanelReviewBatch",
    "revealPanel",
    "summarizePanelJudgeConsistency",
]
