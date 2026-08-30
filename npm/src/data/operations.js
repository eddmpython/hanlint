// @ts-check
/** 승인 고침에서 뜻을 추측하지 않고 재사용할 수 있는 표면 치환. 파이썬 data/operations.py와 같다. */

const URL_PATTERN = /https?:\/\/[^\s)>]+/gu;
const NUMBER_PATTERN = /(?<![A-Za-z가-힣])[-+]?\d+(?:[.,:]\d+)*(?:%|[가-힣]+)?/gu;
const LATIN_PATTERN = /(?<![A-Za-z0-9_])(?:[A-Za-z_][A-Za-z0-9_.:/<>-]*)(?![A-Za-z0-9_])/gu;
const PATH_PATTERN = /(?<!\w)(?:[\w.-]+\/)+[\w.-]+|(?<!\w)[\w-]+\.[A-Za-z0-9]{1,8}(?!\w)/gu;
const INLINE_CODE_PATTERN = /`([^`\n]+)`/gu;
const LINK_DESTINATION_PATTERN = /\[[^\u005D]*\]\(([^)]+)\)/gu;
const HTML_TAG_PATTERN = /<[^>\n]+>/gu;
const DEICTIC_FRAGMENT = /이것|그것|저것|이러한|그러한|해당|이는|그는|그녀|그들/u;
const SURFACE_CHARACTER = /[가-힣A-Za-z0-9]/gu;
const BOUNDARY = new Set(` \t\r\n,.;:!?()[]{}<>"'“”‘’…·/\\|+=*`);
export const MAX_FRAGMENT_CHARACTERS = 32;
export const MAX_SURFACE_EDIT_DISTANCE = 1;

/**
 * @typedef {object} SurfaceOperation
 * @property {string} before
 * @property {string} after
 * @property {string[]} presets
 */

/** @param {string} text */
export function protectedAtoms(text) {
  const found = [];
  for (const [pattern, label, group] of [
    [URL_PATTERN, "url", 0],
    [NUMBER_PATTERN, "number", 0],
    [LATIN_PATTERN, "latin", 0],
    [PATH_PATTERN, "path", 0],
    [INLINE_CODE_PATTERN, "code", 1],
    [LINK_DESTINATION_PATTERN, "link", 1],
  ]) {
    for (const match of text.matchAll(/** @type {RegExp} */ (pattern))) {
      found.push(`${label}:${match[/** @type {number} */ (group)]}`);
    }
  }
  return found.sort();
}

/** @param {string} text */
export function protectedSpans(text) {
  const spans = [];
  for (const pattern of [INLINE_CODE_PATTERN, URL_PATTERN, HTML_TAG_PATTERN]) {
    for (const match of text.matchAll(pattern)) spans.push([match.index, match.index + match[0].length]);
  }
  for (const match of text.matchAll(LINK_DESTINATION_PATTERN)) {
    const offset = match[0].indexOf(match[1]);
    spans.push([match.index + offset, match.index + offset + match[1].length]);
  }
  return spans.sort((left, right) => left[0] - right[0] || left[1] - right[1]);
}

/** @param {string} text @param {string[]} terms */
export function protectedTermAtoms(text, terms) {
  const found = [];
  for (const term of terms) {
    let cursor = 0;
    while (term) {
      const at = text.indexOf(term, cursor);
      if (at < 0) break;
      found.push(term);
      cursor = at + term.length;
    }
  }
  return found.sort();
}

/** @param {string} text @param {number} at */
function startBoundary(text, at) {
  while (at > 0 && !BOUNDARY.has(text[at - 1])) at -= 1;
  return at;
}

/** @param {string} text @param {number} at */
function endBoundary(text, at) {
  while (at < text.length && !BOUNDARY.has(text[at])) at += 1;
  return at;
}

/** @param {string} before @param {string} after */
export function changedFragment(before, after) {
  let prefix = 0;
  const limit = Math.min(before.length, after.length);
  while (prefix < limit && before[prefix] === after[prefix]) prefix += 1;
  let suffix = 0;
  const remaining = Math.min(before.length - prefix, after.length - prefix);
  while (suffix < remaining && before[before.length - suffix - 1] === after[after.length - suffix - 1]) suffix += 1;
  const start = startBoundary(before, prefix);
  const beforeEnd = endBoundary(before, before.length - suffix);
  const afterEnd = endBoundary(after, after.length - suffix);
  return [before.slice(start, beforeEnd).trim(), after.slice(start, afterEnd).trim()];
}

/** @param {string} left @param {string} right */
export function editDistance(left, right) {
  let previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    const current = [leftIndex];
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      current.push(
        Math.min(
          current[current.length - 1] + 1,
          previous[rightIndex] + 1,
          previous[rightIndex - 1] + Number(left[leftIndex - 1] !== right[rightIndex - 1]),
        ),
      );
    }
    previous = current;
  }
  return previous[previous.length - 1];
}

/** @param {string} text */
export function surfaceSkeleton(text) {
  return [...text.matchAll(SURFACE_CHARACTER)].map((match) => match[0]).join("");
}

/**
 * 승인 전후 전체에서 기계가 보증할 수 있는 표면 치환 하나를 추출한다.
 * @param {string} before @param {string} after @param {string[]} [presets] @param {string[]} [protectedTerms]
 * @returns {SurfaceOperation | undefined}
 */
export function operationFromApproval(before, after, presets = [], protectedTerms = []) {
  before = before.normalize("NFC");
  after = after.normalize("NFC");
  if (
    JSON.stringify(protectedAtoms(before)) !== JSON.stringify(protectedAtoms(after)) ||
    JSON.stringify(protectedTermAtoms(before, protectedTerms)) !== JSON.stringify(protectedTermAtoms(after, protectedTerms))
  ) {
    return undefined;
  }
  const [beforeFragment, afterFragment] = changedFragment(before, after);
  const beforeSkeleton = surfaceSkeleton(beforeFragment);
  const afterSkeleton = surfaceSkeleton(afterFragment);
  if (
    !beforeFragment ||
    !afterFragment ||
    beforeFragment === afterFragment ||
    beforeFragment.length > MAX_FRAGMENT_CHARACTERS ||
    afterFragment.length > MAX_FRAGMENT_CHARACTERS ||
    beforeSkeleton.length < 2 ||
    afterSkeleton.length < 2 ||
    editDistance(beforeSkeleton, afterSkeleton) > MAX_SURFACE_EDIT_DISTANCE ||
    DEICTIC_FRAGMENT.test(beforeFragment) ||
    DEICTIC_FRAGMENT.test(afterFragment) ||
    protectedTerms.some((term) => beforeFragment.includes(term) || afterFragment.includes(term)) ||
    protectedAtoms(beforeFragment).length ||
    protectedAtoms(afterFragment).length ||
    before.split(beforeFragment).length - 1 !== 1
  ) {
    return undefined;
  }
  return { before: beforeFragment, after: afterFragment, presets: [...presets] };
}

/** @param {unknown} entries @param {string[]} presetNames @returns {SurfaceOperation[]} */
export function projectOperations(entries, presetNames) {
  if (!Array.isArray(entries)) throw new Error("operations 는 [[operations]] 배열이다");
  const knownPresets = new Set(presetNames);
  const selectors = new Set();
  return entries.map((raw, offset) => {
    const index = offset + 1;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`operations ${index}번째 항목은 표다`);
    const entry = /** @type {Record<string, unknown>} */ (raw);
    const unknown = Object.keys(entry).filter((key) => !["before", "after", "presets"].includes(key)).sort();
    if (unknown.length) throw new Error(`operations ${index}번째 항목의 모르는 키: ${unknown.join(", ")}`);
    const before = entry.before;
    const after = entry.after;
    if (typeof before !== "string" || !before.trim() || before !== before.trim()) {
      throw new Error(`operations ${index}번째 항목의 before 는 양끝 공백 없는 문자열이다`);
    }
    if (typeof after !== "string" || !after.trim() || after !== after.trim()) {
      throw new Error(`operations ${index}번째 항목의 after 는 양끝 공백 없는 문자열이다`);
    }
    const rawPresets = entry.presets;
    if (!Array.isArray(rawPresets) || !rawPresets.length || !rawPresets.every((item) => typeof item === "string")) {
      throw new Error(`operations ${index}번째 항목의 presets 는 비지 않은 문자열 배열이다`);
    }
    const presets = /** @type {string[]} */ (rawPresets);
    const unknownPresets = [...new Set(presets.filter((preset) => !knownPresets.has(preset)))].sort();
    if (unknownPresets.length) throw new Error(`operations ${index}번째 항목의 모르는 프리셋: ${unknownPresets.join(", ")}`);
    if (new Set(presets).size !== presets.length) throw new Error(`operation의 프리셋이 겹친다: ${before}`);
    const operation = operationFromApproval(before, after, presets);
    if (!operation || operation.before !== before || operation.after !== after) {
      throw new Error(`operations ${index}번째 항목은 안전한 표면 치환이 아니다: ${before} -> ${after}`);
    }
    for (const preset of presets) {
      const selector = JSON.stringify([preset, before]);
      if (selectors.has(selector)) throw new Error(`operation 선택 조건이 겹친다: ${preset} ${before}`);
      selectors.add(selector);
    }
    return operation;
  });
}

/** @param {string} character */
function wordCharacter(character) {
  return Boolean(character) && /[\p{L}\p{N}_]/u.test(character);
}

/** @param {string} text @param {SurfaceOperation} operation @param {string[]} [protectedTerms] */
export function operationPositions(text, operation, protectedTerms = []) {
  const positions = [];
  const blocked = protectedSpans(text);
  for (const term of protectedTerms) {
    let cursor = 0;
    while (term) {
      const at = text.indexOf(term, cursor);
      if (at < 0) break;
      blocked.push([at, at + term.length]);
      cursor = at + term.length;
    }
  }
  let cursor = 0;
  while (true) {
    const at = text.indexOf(operation.before, cursor);
    if (at < 0) return positions;
    const end = at + operation.before.length;
    const left = at > 0 ? text[at - 1] : "";
    const right = end < text.length ? text[end] : "";
    const touchesWord =
      (wordCharacter(operation.before[0]) && wordCharacter(left)) ||
      (wordCharacter(operation.before[operation.before.length - 1]) && wordCharacter(right));
    const insideProtected = blocked.some(([start, stop]) => at < stop && end > start);
    if (!touchesWord && !insideProtected) positions.push(at);
    cursor = at + 1;
  }
}

/** @param {string} text @param {SurfaceOperation} operation @param {string[]} [protectedTerms] */
export function applyOperation(text, operation, protectedTerms = []) {
  const positions = operationPositions(text, operation, protectedTerms);
  if (positions.length !== 1) return undefined;
  const at = positions[0];
  const end = at + operation.before.length;
  const changed = text.slice(0, at) + operation.after + text.slice(end);
  const factsPreserved = JSON.stringify(protectedAtoms(text)) === JSON.stringify(protectedAtoms(changed));
  const termsPreserved =
    JSON.stringify(protectedTermAtoms(text, protectedTerms)) === JSON.stringify(protectedTermAtoms(changed, protectedTerms));
  return factsPreserved && termsPreserved ? changed : undefined;
}

/** @param {string} sourceText @param {string | null | undefined} preset @param {SurfaceOperation[]} operations @param {string[]} [protectedTerms] */
export function operationFor(sourceText, preset, operations, protectedTerms = []) {
  if (!preset) return undefined;
  const matches = [];
  for (const operation of operations) {
    if (!operation.presets.includes(preset)) continue;
    const result = applyOperation(sourceText, operation, protectedTerms);
    if (result !== undefined) matches.push({ operation, sourceText, result });
  }
  return matches.length === 1 ? matches[0] : undefined;
}

/** @param {{operation: SurfaceOperation, sourceText: string, result: string}} applied @param {string} preset */
export function operationData(applied, preset) {
  return {
    kind: "surfaceSubstitution",
    before: applied.operation.before,
    after: applied.operation.after,
    sourceText: applied.sourceText,
    result: applied.result,
    match: { preset, unique: true, wordBoundary: true, protectedFacts: true },
  };
}
