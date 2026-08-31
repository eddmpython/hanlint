// 눈가림 평가 작업대의 판정 논리. 휠에 실려 나가는 파이썬 자료 파일을 그대로 읽어 잰다.
//
// mainPlan/14 의 종료 조건 가운데 "진행 저장, 다시 열기, 내보내기와 fail-closed 제약을 시험한다" 가
// 여기다. 논리가 인라인 스크립트 안에 있던 때는 브라우저를 열어야만 확인할 수 있었다 (2026-08-31).
// 남은 것은 순수 시각 확인 (레이아웃, 색, 실제 브라우저의 키보드 초점) 뿐이다.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const LOGIC = fileURLToPath(new URL("../../src/hanlint/data/panelReviewPage.js", import.meta.url));
// 파일은 globalThis 에 붙는다. import 하면 그 뒤로 globalThis.hanlintReview 를 쓸 수 있다.
await import(`data:text/javascript,${encodeURIComponent(readFileSync(LOGIC, "utf-8"))}`);
const logic = globalThis.hanlintReview;

const DIMENSIONS = ["naturalness", "clarity", "taskUtility", "voice"];

function panelCase(voiceReference = "목소리 표본입니다.") {
  return {
    caseId: "case-001",
    assignmentCaseSha256: "a".repeat(64),
    context: { reader: "독자", task: "과업", facts: [], voiceReference },
    comparison: { left: "왼쪽 글", right: "오른쪽 글" },
  };
}

function filled(overrides = {}) {
  const review = logic.emptyReview(panelCase(), DIMENSIONS);
  review.contentChecks = { left: "pass", right: "pass" };
  for (const dimension of DIMENSIONS) review.preferences[dimension] = "left";
  for (const name of ["content", ...DIMENSIONS]) review.reasons[name] = "읽고 판단한 이유입니다.";
  return { ...review, ...overrides };
}

test("빈 검토는 사람 label 을 미리 채우지 않는다", () => {
  const review = logic.emptyReview(panelCase(), DIMENSIONS);
  assert.deepEqual(review.contentChecks, { left: "", right: "" });
  assert.deepEqual(Object.values(review.preferences), ["", "", "", ""]);
  assert.deepEqual(Object.values(review.reasons), ["", "", "", "", ""]);
});

test("content 를 끝내기 전에는 선호를 고를 수 없다", () => {
  const review = logic.emptyReview(panelCase(), DIMENSIONS);
  const locks = logic.preferenceLock(panelCase(), review, DIMENSIONS);
  for (const dimension of DIMENSIONS) {
    assert.equal(locks[dimension].disabled, true, `${dimension} 는 잠겨야 한다`);
    if (dimension !== "voice") assert.equal(locks[dimension].value, "");
  }
});

test("한쪽이라도 content 에 걸리면 모든 차원이 판단 불가로 잠긴다", () => {
  const review = logic.emptyReview(panelCase(), DIMENSIONS);
  review.contentChecks = { left: "pass", right: "fail" };
  const locks = logic.preferenceLock(panelCase(), review, DIMENSIONS);
  for (const dimension of DIMENSIONS) {
    assert.equal(locks[dimension].value, "cannotJudge");
    assert.equal(locks[dimension].disabled, true);
  }
});

test("목소리 표본이 없으면 voice 만 기권으로 잠기고 나머지는 열린다", () => {
  const withoutVoice = panelCase(null);
  const review = logic.emptyReview(withoutVoice, DIMENSIONS);
  review.contentChecks = { left: "pass", right: "pass" };
  const locks = logic.preferenceLock(withoutVoice, review, DIMENSIONS);
  assert.deepEqual(locks.voice, { value: "cannotJudge", disabled: true });
  for (const dimension of ["naturalness", "clarity", "taskUtility"]) {
    assert.equal(locks[dimension].disabled, false, `${dimension} 는 열려야 한다`);
  }
});

test("진행을 저장하고 다시 열면 그대로 돌아온다", () => {
  const assignment = { version: 1, assignmentSha256: "b".repeat(64), evaluator: { id: "ev" }, cases: [panelCase()] };
  const saved = { currentIndex: 0, reviews: { "case-001": filled() } };
  const restored = logic.restoreState(JSON.parse(JSON.stringify(saved)), assignment, DIMENSIONS);
  assert.deepEqual(restored, saved);
});

test("다른 배정의 저장분과 꼴이 틀린 저장분은 안 읽고 빈 상태로 시작한다", () => {
  const assignment = { version: 1, assignmentSha256: "b".repeat(64), evaluator: { id: "ev" }, cases: [panelCase()] };
  const empty = { currentIndex: 0, reviews: {} };
  const otherCase = { ...filled(), caseId: "case-999" };
  assert.deepEqual(logic.restoreState({ currentIndex: 0, reviews: { "case-999": otherCase } }, assignment, DIMENSIONS), empty);

  const otherHash = { ...filled(), assignmentCaseSha256: "c".repeat(64) };
  assert.deepEqual(logic.restoreState({ currentIndex: 0, reviews: { "case-001": otherHash } }, assignment, DIMENSIONS), empty);

  const extraKey = filled();
  extraKey.preferences.감정 = "left";
  assert.deepEqual(logic.restoreState({ currentIndex: 0, reviews: { "case-001": extraKey } }, assignment, DIMENSIONS), empty);

  assert.deepEqual(logic.restoreState({ currentIndex: "0", reviews: {} }, assignment, DIMENSIONS), empty);
  assert.deepEqual(logic.restoreState(null, assignment, DIMENSIONS), empty);
});

test("저장된 자리 번호는 사례 범위 안으로 잡아 준다", () => {
  const assignment = { version: 1, assignmentSha256: "b".repeat(64), evaluator: { id: "ev" }, cases: [panelCase()] };
  assert.equal(logic.restoreState({ currentIndex: 9, reviews: {} }, assignment, DIMENSIONS).currentIndex, 0);
  assert.equal(logic.restoreState({ currentIndex: -3, reviews: {} }, assignment, DIMENSIONS).currentIndex, 0);
});

test("이유가 비었거나 자리표시자면 안 끝난 것이다", () => {
  assert.equal(logic.reasonReady("읽고 판단했다"), true);
  for (const value of ["", "   ", "<required>", "  <required>  ", null, 3]) {
    assert.equal(logic.reasonReady(value), false, `${JSON.stringify(value)} 는 안 채운 것이다`);
  }
});

test("모든 차원과 이유가 차야 그 사례가 끝난다", () => {
  assert.equal(logic.caseComplete(panelCase(), filled(), DIMENSIONS), true);
  const noReason = filled();
  noReason.reasons.voice = "<required>";
  assert.equal(logic.caseComplete(panelCase(), noReason, DIMENSIONS), false);
  const noPreference = filled();
  noPreference.preferences.clarity = "";
  assert.equal(logic.caseComplete(panelCase(), noPreference, DIMENSIONS), false);
  const halfContent = filled({ contentChecks: { left: "pass", right: "" } });
  assert.equal(logic.caseComplete(panelCase(), halfContent, DIMENSIONS), false);
});

test("content 에 걸린 사례는 모든 차원이 기권일 때만 끝난다", () => {
  const failed = filled({ contentChecks: { left: "fail", right: "pass" } });
  assert.equal(logic.caseComplete(panelCase(), failed, DIMENSIONS), false, "선호가 남아 있으면 안 끝난다");
  for (const dimension of DIMENSIONS) failed.preferences[dimension] = "cannotJudge";
  assert.equal(logic.caseComplete(panelCase(), failed, DIMENSIONS), true);
});

test("내보낸 JSON 이 import 계약과 같은 꼴이고 이유의 앞뒤 공백을 걷는다", () => {
  const assignment = {
    version: 1,
    assignmentSha256: "b".repeat(64),
    evaluator: { id: "ev", group: "targetReader", protocolRevision: 1 },
    cases: [panelCase()],
  };
  const review = filled();
  review.reasons.content = "  앞뒤에 공백이 있다.  ";
  const payload = logic.exportPayload(assignment, () => review);
  assert.deepEqual(Object.keys(payload), ["version", "kind", "assignmentSha256", "evaluator", "reviews"]);
  assert.equal(payload.kind, "hanlint.panelAssignmentReview");
  assert.equal(payload.assignmentSha256, assignment.assignmentSha256);
  assert.deepEqual(payload.evaluator, assignment.evaluator);
  assert.equal(payload.reviews.length, 1);
  assert.equal(payload.reviews[0].reasons.content, "앞뒤에 공백이 있다.");
  assert.deepEqual(Object.keys(payload.reviews[0]), ["caseId", "assignmentCaseSha256", "contentChecks", "preferences", "reasons"]);
});
