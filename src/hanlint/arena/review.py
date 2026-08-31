"""writingArena 사람 평가자의 배정, 오프라인 화면과 결과 import 계약."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files

from . import checkedString, exactKeys, stableDigest
from .panel import (
    EVALUATOR_GROUPS,
    PANEL_DIMENSIONS,
    PANEL_PROTOCOL_REVISION,
    PANEL_RUBRIC,
    PANEL_RUBRIC_SHA256,
    PANEL_VERSION,
    checkedPanelSuite,
    recordPanelReviewBatch,
)

ASSIGNMENT_KIND = "hanlint.panelAssignment"
ASSIGNMENT_REVIEW_KIND = "hanlint.panelAssignmentReview"
PAGE_TEMPLATE = "data/panelReviewPage.html"
PAGE_LOGIC = "data/panelReviewPage.js"
PAGE_PLACEHOLDER = "__HANLINT_ASSIGNMENT__"
LOGIC_PLACEHOLDER = "__HANLINT_PAGE_LOGIC__"
"""판정 논리는 별도 파일이고 렌더할 때 인라인한다. 단일 HTML 과 외부 요청 0 은 그대로다.

인라인 스크립트 안에 두면 `node --test` 가 못 읽어 content 우선 잠금, 목소리 기권, 진행 재개,
내보내기 계약을 브라우저 없이는 잴 수 없다. 파일로 빼면 같은 글자를 두 곳이 쓴다 (2026-08-31)."""


def assignmentDigest(data: dict) -> str:
    canonical = deepcopy(data)
    canonical.pop("assignmentSha256", None)
    if "reviewTemplate" in canonical:
        canonical["reviewTemplate"]["assignmentSha256"] = "<assignmentSha256>"
    return stableDigest(canonical)


def checkedEvaluator(evaluatorId: object, group: object) -> dict:
    evaluatorId = checkedString(evaluatorId, "panel assignment evaluator.id")
    if evaluatorId == "<required>":
        raise ValueError("panel assignment evaluator.id의 <required>를 실제 가명으로 바꾼다")
    if group not in EVALUATOR_GROUPS:
        raise ValueError(f"panel assignment evaluator.group은 {', '.join(EVALUATOR_GROUPS)} 가운데 하나다")
    return {
        "id": evaluatorId,
        "group": group,
        "protocolRevision": PANEL_PROTOCOL_REVISION,
    }


def reversedFor(suiteSha256: str, evaluatorId: str) -> bool:
    """이 평가자가 suite 의 좌우를 통째로 뒤집어 보는가. 사례마다 다르지 않다.

    사례마다 번갈아 뒤집던 때는 suite 의 좌우 교대 (`desiredCandidateLeft`) 와 같은 홀짝 함수를 같은
    색인에 써서 XOR 이 색인에 대해 상수가 됐다. 그래서 한 평가자가 모든 사례에서 후보를 같은 쪽으로만
    봤고 (실측: pilot 일곱 사례가 LLLLLLL 또는 RRRRRRR), 위치 편향이 후보 요인과 완전히 교락됐다.
    통째로 뒤집으면 suite 의 교대가 그대로 남아 평가자 안에서 좌우가 갈리고, 평가자는 두 순서로
    나뉜다 (2026-08-31).
    """
    return int(sha256(f"panel-assignment:{suiteSha256}:{evaluatorId}".encode()).hexdigest(), 16) % 2 == 1


def assignmentReviewTemplate(evaluator: dict, cases: list[dict]) -> dict:
    return {
        "version": PANEL_VERSION,
        "kind": ASSIGNMENT_REVIEW_KIND,
        "assignmentSha256": "<assignmentSha256>",
        "evaluator": deepcopy(evaluator),
        "reviews": [
            {
                "caseId": item["caseId"],
                "assignmentCaseSha256": item["assignmentCaseSha256"],
                "contentChecks": {"left": "", "right": ""},
                "preferences": {dimension: "" for dimension in PANEL_DIMENSIONS},
                "reasons": {"content": "<required>"} | {dimension: "<required>" for dimension in PANEL_DIMENSIONS},
            }
            for item in cases
        ],
    }


def preparePanelAssignment(suite: dict, evaluatorId: str, group: str) -> dict:
    """평가자 한 명에게 내부 순서를 밝히지 않은 결정적 case 배정을 만든다."""
    suite = checkedPanelSuite(suite)
    if not suite["cases"]:
        raise ValueError("panel assignment에는 평가할 case가 하나 이상 필요하다")
    evaluator = checkedEvaluator(evaluatorId, group)
    cases = []
    for index, panelCase in enumerate(suite["cases"]):
        comparison = deepcopy(panelCase["comparison"])
        if reversedFor(suite["suiteSha256"], evaluator["id"]):
            comparison = {"left": comparison["right"], "right": comparison["left"]}
        assigned = {
            "caseId": f"case-{index + 1:03d}",
            "context": deepcopy(panelCase["context"]),
            "comparison": comparison,
        }
        assigned["assignmentCaseSha256"] = stableDigest(assigned)
        cases.append(assigned)
    payload = {
        "version": PANEL_VERSION,
        "kind": ASSIGNMENT_KIND,
        "studyCode": f"panel-{suite['suiteSha256'][:12]}",
        "suiteSha256": suite["suiteSha256"],
        "rubric": deepcopy(PANEL_RUBRIC),
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "evaluator": evaluator,
        "source": {
            "cases": len(cases),
            "identityHidden": ["strategy", "model", "author"],
        },
        "cases": cases,
        "reviewTemplate": assignmentReviewTemplate(evaluator, cases),
        "claimBoundary": (
            "이 assignment는 한 평가자에게 한 좌우 순서만 보인다. 후보 정체성, 내부 순서와 다른 평가자의 선택을 담지 않는다"
        ),
    }
    payload["assignmentSha256"] = assignmentDigest(payload)
    payload["reviewTemplate"]["assignmentSha256"] = payload["assignmentSha256"]
    return payload


def checkedPanelAssignment(suite: dict, data: object) -> dict:
    """assignment가 suite와 평가자에서 만든 고정 결과인지 검증한다."""
    suite = checkedPanelSuite(suite)
    data = exactKeys(
        data,
        {
            "version",
            "kind",
            "studyCode",
            "suiteSha256",
            "rubric",
            "rubricSha256",
            "evaluator",
            "source",
            "cases",
            "reviewTemplate",
            "claimBoundary",
            "assignmentSha256",
        },
        "panel assignment",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != ASSIGNMENT_KIND:
        raise ValueError("panel assignment의 version 또는 kind가 다르다")
    evaluator = exactKeys(data["evaluator"], {"id", "group", "protocolRevision"}, "panel assignment evaluator")
    if evaluator["protocolRevision"] != PANEL_PROTOCOL_REVISION:
        raise ValueError("panel assignment evaluator.protocolRevision이 다르다")
    expected = preparePanelAssignment(suite, evaluator["id"], evaluator["group"])
    if data != expected:
        raise ValueError("panel assignment가 suite와 evaluator에서 만든 고정 결과와 다르다")
    return data


def reverseSide(choice: str) -> str:
    if choice == "left":
        return "right"
    if choice == "right":
        return "left"
    return choice


def normalizeSides(values: object, reversedOrder: bool, where: str) -> dict:
    values = exactKeys(values, {"left", "right"}, where)
    if not reversedOrder:
        return {"left": values["left"], "right": values["right"]}
    return {"left": values["right"], "right": values["left"]}


def normalizePreferences(values: object, reversedOrder: bool, where: str) -> dict:
    values = exactKeys(values, set(PANEL_DIMENSIONS), where)
    return {dimension: reverseSide(values[dimension]) if reversedOrder else values[dimension] for dimension in PANEL_DIMENSIONS}


def recordPanelAssignmentReview(suite: dict, assignment: dict, data: object) -> dict:
    """평가자가 본 좌우 선택을 원래 suite 방향으로 되돌리고 기존 사람 batch로 잠근다."""
    suite = checkedPanelSuite(suite)
    assignment = checkedPanelAssignment(suite, assignment)
    data = exactKeys(
        data,
        {"version", "kind", "assignmentSha256", "evaluator", "reviews"},
        "panel assignment review",
    )
    if data["version"] != PANEL_VERSION or data["kind"] != ASSIGNMENT_REVIEW_KIND:
        raise ValueError("panel assignment review의 version 또는 kind가 다르다")
    if data["assignmentSha256"] != assignment["assignmentSha256"]:
        raise ValueError("panel assignment review의 assignmentSha256가 다르다")
    if data["evaluator"] != assignment["evaluator"]:
        raise ValueError("panel assignment review의 evaluator가 assignment와 다르다")
    if not isinstance(data["reviews"], list):
        raise ValueError("panel assignment review의 reviews는 배열이다")
    panelCases = {assigned["caseId"]: panelCase for assigned, panelCase in zip(assignment["cases"], suite["cases"], strict=True)}
    assignedCases = {item["caseId"]: item for item in assignment["cases"]}
    normalized = []
    seen = set()
    for index, review in enumerate(data["reviews"], start=1):
        where = f"panel assignment review {index}번째"
        review = exactKeys(
            review,
            {"caseId", "assignmentCaseSha256", "contentChecks", "preferences", "reasons"},
            where,
        )
        caseId = checkedString(review["caseId"], f"{where}.caseId")
        if caseId not in assignedCases:
            raise ValueError(f"{where}가 assignment에 없는 case를 가리킨다: {caseId}")
        if caseId in seen:
            raise ValueError(f"panel assignment review의 caseId가 겹친다: {caseId}")
        seen.add(caseId)
        if review["assignmentCaseSha256"] != assignedCases[caseId]["assignmentCaseSha256"]:
            raise ValueError(f"{where}.assignmentCaseSha256가 다르다")
        reversedOrder = reversedFor(suite["suiteSha256"], assignment["evaluator"]["id"])
        normalized.append(
            {
                "caseId": panelCases[caseId]["caseId"],
                "caseSha256": panelCases[caseId]["caseSha256"],
                "contentChecks": normalizeSides(review["contentChecks"], reversedOrder, f"{where}.contentChecks"),
                "preferences": normalizePreferences(review["preferences"], reversedOrder, f"{where}.preferences"),
                "reasons": review["reasons"],
            }
        )
    if seen != set(assignedCases):
        missing = sorted(set(assignedCases) - seen)
        raise ValueError(f"panel assignment review에 빠진 case다: {', '.join(missing)}")
    rawBatch = {
        "version": PANEL_VERSION,
        "kind": "hanlint.panelReviewBatch",
        "suiteSha256": suite["suiteSha256"],
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "evaluator": deepcopy(assignment["evaluator"]),
        "reviews": normalized,
    }
    return recordPanelReviewBatch(suite, rawBatch)


def scriptJson(data: dict) -> str:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        encoded.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def renderPanelReviewHtml(suite: dict, assignment: dict) -> str:
    """검증한 assignment를 네트워크 없는 단일 HTML 평가 화면으로 만든다."""
    assignment = checkedPanelAssignment(suite, assignment)
    template = files("hanlint").joinpath(PAGE_TEMPLATE).read_text(encoding="utf-8")
    if template.count(PAGE_PLACEHOLDER) != 1:
        raise RuntimeError("panel review page template의 assignment 자리가 하나가 아니다")
    if template.count(LOGIC_PLACEHOLDER) != 1:
        raise RuntimeError("panel review page template의 판정 논리 자리가 하나가 아니다")
    logic = files("hanlint").joinpath(PAGE_LOGIC).read_text(encoding="utf-8")
    if "</script" in logic.lower():
        raise RuntimeError("판정 논리에 스크립트 닫는 태그가 있으면 인라인할 때 페이지가 깨진다")
    return template.replace(LOGIC_PLACEHOLDER, logic).replace(PAGE_PLACEHOLDER, scriptJson(assignment))


def preparePanelReviewHtml(suite: dict, evaluatorId: str, group: str) -> str:
    """suite와 평가자 정보에서 바로 단일 HTML 평가 화면을 만든다."""
    assignment = preparePanelAssignment(suite, evaluatorId, group)
    return renderPanelReviewHtml(suite, assignment)


__all__ = [
    "ASSIGNMENT_KIND",
    "ASSIGNMENT_REVIEW_KIND",
    "checkedPanelAssignment",
    "preparePanelAssignment",
    "preparePanelReviewHtml",
    "recordPanelAssignmentReview",
    "renderPanelReviewHtml",
]
