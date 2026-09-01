// @ts-check
/** Reader Contract가 잠근 제목 순서와 글 지문의 구조 요약. */

/** @typedef {{position: number, expected: string | null, actual: string | null}} OutlineMismatch */
/** @typedef {{matches: boolean, level: number, expected: string[], actual: string[], mismatches: OutlineMismatch[]}} OutlineDiff */
/** @typedef {{heading: string, line: number, paragraphCount: number, codeBlockCount: number}} SectionSummary */
/** @typedef {{sentenceCount: number, paragraphCount: number, sectionCount: number, wordCount: number, questionCount: number, readerCallCount: number, sections: SectionSummary[]}} DocumentSummary */

/** @param {import("../config/readerContract.js").Outline} outline @param {import("../fingerprint/build.js").DocumentPrint} doc @returns {OutlineDiff} */
export function compareOutline(outline, doc) {
  const actual = doc.headings.filter(([level]) => level === outline.level).map(([, title]) => title);
  const mismatches = [];
  const count = Math.max(outline.headings.length, actual.length);
  for (let index = 0; index < count; index += 1) {
    const expected = outline.headings[index] ?? null;
    const found = actual[index] ?? null;
    if (expected !== found) {
      mismatches.push({ position: index + 1, expected, actual: found });
    }
  }
  return {
    matches: mismatches.length === 0,
    level: outline.level,
    expected: [...outline.headings],
    actual,
    mismatches,
  };
}

/** @param {import("../fingerprint/build.js").DocumentPrint} doc @returns {DocumentSummary} */
export function summarizeDocument(doc) {
  return {
    sentenceCount: doc.sentences.length,
    paragraphCount: doc.paragraphs.length,
    sectionCount: doc.bodySections.length,
    wordCount: doc.wordCount,
    questionCount: doc.questionCount,
    readerCallCount: doc.readerCallCount,
    sections: doc.bodySections.map((section) => ({
      heading: section.title,
      line: section.startLine,
      paragraphCount: section.paragraphs.length,
      codeBlockCount: section.blockKinds.filter((kind) => kind === "code").length,
    })),
  };
}
