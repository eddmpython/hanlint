// @ts-check
/**
 * 지문 계층의 JSON 꼴. 파이썬 report/fingerprintJson.py 와 같은 키 순서다. 층마다 한 번씩만 적고 위층은
 * 아래층을 index 로 가리킨다. 실수는 소수 여섯째 자리로 맞춰 두 구현이 같은 글자를 낸다.
 */

export const LAYERS = ["all", "sentences", "paragraphs", "sections", "document"];

/** @param {number | null} value */
function num(value) {
  if (value === null) return null;
  return Math.round(value * 1e6) / 1e6;
}

/** @param {Set<string>} set */
function sortedList(set) {
  return [...set].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

/** @param {import("../fingerprint/build.js").SentencePrint} s */
function sentenceDict(s) {
  return {
    index: s.index,
    line: s.line,
    text: s.text,
    blockIndex: s.blockIndex,
    paragraphIndex: s.paragraphIndex,
    sectionIndex: s.sectionIndex,
    length: s.length,
    ending: s.ending,
    mood: s.mood,
    register: s.register,
    commas: s.commas,
    connectorStart: s.connectorStart,
    causal: s.causal,
    deixis: [...s.deixis],
    euiCount: s.euiCount,
    nounRun: s.nounRun,
    passives: [...s.passives],
    hedges: s.hedges,
    numbers: s.numbers,
    topics: sortedList(s.topics),
    promises: [...s.promises],
    recalls: [...s.recalls],
    countPromises: s.countPromises.map(([n, unit, text]) => [n, unit, text]),
    readerCall: s.readerCall,
    matches: s.matches.map((m) => ({
      dictionary: m.dictionary,
      text: m.text,
      start: m.start,
      end: m.end,
      why: m.why,
      source: m.source,
      fix: m.fix,
    })),
    quoted: s.quoted.map(([start, end]) => [start, end]),
  };
}

/** @param {import("../fingerprint/build.js").ParagraphPrint} p */
function paragraphDict(p) {
  return {
    index: p.index,
    blockIndex: p.blockIndex,
    sectionIndex: p.sectionIndex,
    startLine: p.startLine,
    endLine: p.endLine,
    sentences: p.sentences.map((s) => s.index),
    sentenceCount: p.sentenceCount,
    meanLength: num(p.meanLength),
    lengthStd: num(p.lengthStd),
    causalTotal: p.causalTotal,
    deixisTotal: p.deixisTotal,
    topics: sortedList(p.topics),
    overlapWithPrevious: num(p.overlapWithPrevious),
    followsProseDirectly: p.followsProseDirectly,
  };
}

/** @param {import("../fingerprint/build.js").SectionPrint} s */
function sectionDict(s) {
  return {
    index: s.index,
    title: s.title,
    level: s.level,
    startLine: s.startLine,
    paragraphs: s.paragraphs.map((p) => p.index),
    blockKinds: [...s.blockKinds],
    topics: sortedList(s.topics),
    isIntro: s.isIntro,
  };
}

/** @param {import("../fingerprint/build.js").DocumentPrint} doc */
function documentDict(doc) {
  return {
    path: doc.path,
    frontmatter: { ...doc.frontmatter },
    headings: doc.headings.map(([level, text, line]) => [level, text, line]),
    wordCount: doc.wordCount,
    sentenceCount: doc.sentences.length,
    paragraphCount: doc.paragraphs.length,
    sectionCount: doc.sections.length,
    questionCount: doc.questionCount,
    readerCallCount: doc.readerCallCount,
    register: doc.register,
    registerShare: Math.round(doc.registerShare * 1000) / 1000,
    countPromises: doc.countPromises.map(([n, unit, line, text]) => [n, unit, line, text]),
    promises: doc.reader.final.promises.map(([line, text]) => [line, text]),
    recalls: doc.reader.final.recalls.map(([line, text]) => [line, text]),
    disabled: doc.disabled.map(([name, start, end]) => [name, start, end]),
  };
}

/** @param {import("../fingerprint/build.js").DocumentPrint} doc @param {string} [layer] */
export function fingerprintDict(doc, layer = "all") {
  /** @type {Record<string, unknown>} */
  const data = { version: 1, layer };
  if (layer === "all" || layer === "document") data.document = documentDict(doc);
  if (layer === "all" || layer === "sections") data.sections = doc.sections.map(sectionDict);
  if (layer === "all" || layer === "paragraphs") data.paragraphs = doc.paragraphs.map(paragraphDict);
  if (layer === "all" || layer === "sentences") data.sentences = doc.sentences.map(sentenceDict);
  return data;
}

/** @param {import("../fingerprint/build.js").DocumentPrint} doc @param {string} [layer] */
export function renderFingerprintJson(doc, layer = "all") {
  return JSON.stringify(fingerprintDict(doc, layer), null, 2);
}
