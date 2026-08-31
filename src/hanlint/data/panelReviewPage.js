// 눈가림 평가 작업대의 판정 논리. DOM 을 만지지 않는 순수 함수만 둔다.
//
// 왜 파일로 뺐나. 이 논리는 휠에 실려 나가는데 인라인 스크립트 안에 있어 아무도 못 쟀다. 게이트 다섯은
// 정체성 누출과 변조만 보고 content 우선 잠금, 목소리 기권, 진행 저장과 재개, 내보내기 계약은 브라우저를
// 열어야만 확인할 수 있었다. 순수 함수 시험과 실제 브라우저 탐침이 두 층을 나눠 확인한다.
//
// 이 파일은 브라우저에서 인라인 스크립트로 그대로 붙고 (renderPanelReviewHtml 이 넣는다) node --test 가
// 같은 파일을 import 한다. 그래서 import 도 export 도 쓰지 않고 globalThis 에 붙인다. DOM 배선은
// panelReviewPage.html 이 그대로 맡는다. 스크립트 태그 글자는 여기 적지 않는다. 인라인될 때 세어진다.
"use strict";

const hanlintReview = {
  /** 아직 아무것도 안 고른 검토 한 건. */
  emptyReview(panelCase, dimensions) {
    return {
      caseId: panelCase.caseId,
      assignmentCaseSha256: panelCase.assignmentCaseSha256,
      contentChecks: { left: "", right: "" },
      preferences: Object.fromEntries(dimensions.map((dimension) => [dimension, ""])),
      reasons: Object.fromEntries(["content", ...dimensions].map((name) => [name, ""])),
    };
  },

  /** 브라우저에 저장된 검토가 이 사례의 것이고 꼴이 정확한가. 키가 하나라도 남거나 모자라면 거짓이다. */
  storedReviewValid(review, panelCase, dimensions) {
    const exactKeys = (value, keys) =>
      value !== null &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value).length === keys.length &&
      keys.every((key) => Object.hasOwn(value, key));
    return (
      exactKeys(review, ["caseId", "assignmentCaseSha256", "contentChecks", "preferences", "reasons"]) &&
      review.caseId === panelCase.caseId &&
      review.assignmentCaseSha256 === panelCase.assignmentCaseSha256 &&
      exactKeys(review.contentChecks, ["left", "right"]) &&
      dimensions.every((dimension) => Object.hasOwn(review.preferences || {}, dimension)) &&
      Object.keys(review.preferences || {}).length === dimensions.length &&
      ["content", ...dimensions].every((name) => Object.hasOwn(review.reasons || {}, name)) &&
      Object.keys(review.reasons || {}).length === dimensions.length + 1
    );
  },

  /** 저장분을 되살린다. 이 배정의 것이 아니거나 꼴이 틀리면 빈 상태를 낸다. */
  restoreState(parsed, assignment, dimensions) {
    const empty = { currentIndex: 0, reviews: {} };
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return empty;
    const casesById = Object.fromEntries(assignment.cases.map((panelCase) => [panelCase.caseId, panelCase]));
    const entries =
      parsed.reviews !== null && typeof parsed.reviews === "object" && !Array.isArray(parsed.reviews)
        ? Object.entries(parsed.reviews)
        : null;
    if (
      entries === null ||
      !Number.isInteger(parsed.currentIndex) ||
      !entries.every(([caseId, review]) => casesById[caseId] && hanlintReview.storedReviewValid(review, casesById[caseId], dimensions))
    ) {
      return empty;
    }
    const last = assignment.cases.length - 1;
    return { ...parsed, currentIndex: Math.max(0, Math.min(last, parsed.currentIndex)) };
  },

  /** 두 글 다 content 를 통과했는가. */
  bothContentPass(review) {
    return ["left", "right"].every((side) => review.contentChecks[side] === "pass");
  },

  /**
   * 차원마다 선호를 고를 수 있는가와 강제되는 값. 화면은 이 결과를 그리기만 한다.
   *
   * content 를 끝내기 전에는 못 고른다. 하나라도 fail 이면 판단 불가로 잠근다. 목소리 표본이 없으면
   * voice 는 언제나 판단 불가로 잠근다.
   */
  preferenceLock(panelCase, review, dimensions) {
    const contentComplete = ["left", "right"].every((side) => review.contentChecks[side]);
    const bothPass = contentComplete && hanlintReview.bothContentPass(review);
    return Object.fromEntries(
      dimensions.map((dimension) => {
        if (dimension === "voice" && panelCase.context.voiceReference === null) {
          return [dimension, { value: "cannotJudge", disabled: true }];
        }
        if (!contentComplete) return [dimension, { value: "", disabled: true }];
        if (!bothPass) return [dimension, { value: "cannotJudge", disabled: true }];
        return [dimension, { value: review.preferences[dimension], disabled: false }];
      }),
    );
  },

  /** 이유가 채워졌는가. 빈칸과 자리표시자는 안 채운 것이다. */
  reasonReady(value) {
    return typeof value === "string" && value.trim().length > 0 && value.trim() !== "<required>";
  },

  /** 이 사례를 다 봤는가. */
  caseComplete(panelCase, review, dimensions) {
    const decided = ["pass", "fail", "cannotJudge"];
    if (!["left", "right"].every((side) => decided.includes(review.contentChecks[side]))) return false;
    const bothPass = hanlintReview.bothContentPass(review);
    const preferencesComplete = dimensions.every((dimension) => {
      if (!bothPass) return review.preferences[dimension] === "cannotJudge";
      if (dimension === "voice" && panelCase.context.voiceReference === null) {
        return review.preferences[dimension] === "cannotJudge";
      }
      return ["left", "right", "tie", "cannotJudge"].includes(review.preferences[dimension]);
    });
    return preferencesComplete && ["content", ...dimensions].every((name) => hanlintReview.reasonReady(review.reasons[name]));
  },

  /** 내보낼 JSON. panelAssignmentReview import 계약과 같은 꼴이다. 사람 label 을 만들지 않는다. */
  exportPayload(assignment, reviewOf) {
    return {
      version: assignment.version,
      kind: "hanlint.panelAssignmentReview",
      assignmentSha256: assignment.assignmentSha256,
      evaluator: assignment.evaluator,
      reviews: assignment.cases.map((panelCase) => {
        const review = reviewOf(panelCase);
        return {
          ...review,
          reasons: Object.fromEntries(Object.entries(review.reasons).map(([name, value]) => [name, value.trim()])),
        };
      }),
    };
  },
};

globalThis.hanlintReview = hanlintReview;
