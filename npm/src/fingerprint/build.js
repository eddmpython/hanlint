// @ts-check
/** 문서 모델을 한 번 훑어 글 지문을 만든다. 텍스트를 읽는 유일한 자리다. 파이썬 fingerprint/build.py 와 같다. */
import { defaultConfig } from "../config/settings.js";
import { HEADING, PROSE, sectionStartLine, sectionTitle } from "../document/model.js";
import { plainText } from "../document/plainText.js";
import { countIn, mean, pstdev, wordCount } from "../text.js";
import { entriesFor, matchesIn } from "./dictionaries.js";
import * as markers from "./markers.js";
import { overlap, topicsOf, unionOf } from "./topics.js";

/**
 * @typedef {object} SentencePrint
 * @property {number} index
 * @property {number} line
 * @property {string} text
 * @property {number} blockIndex
 * @property {number} paragraphIndex
 * @property {number} sectionIndex
 * @property {number} length 어절 수
 * @property {string} ending
 * @property {string} mood
 * @property {number} commas
 * @property {string | null} connectorStart
 * @property {number} causal
 * @property {string[]} deixis
 * @property {number} euiCount
 * @property {number} nounRun
 * @property {string[]} passives
 * @property {number} hedges
 * @property {number} numbers
 * @property {Set<string>} topics
 * @property {string[]} promises
 * @property {string[]} recalls
 * @property {[number, string, string][]} countPromises
 * @property {boolean} readerCall
 * @property {import("./dictionaries.js").DictionaryMatch[]} matches
 */

/**
 * @typedef {object} ParagraphPrint
 * @property {number} index
 * @property {number} blockIndex
 * @property {number} sectionIndex
 * @property {number} startLine
 * @property {number} endLine
 * @property {SentencePrint[]} sentences
 * @property {number} sentenceCount
 * @property {number} meanLength
 * @property {number} lengthStd
 * @property {number} causalTotal
 * @property {number} deixisTotal
 * @property {Set<string>} topics
 * @property {number | null} overlapWithPrevious
 * @property {boolean} followsProseDirectly
 * @property {string} text
 */

/**
 * @typedef {object} SectionPrint
 * @property {number} index
 * @property {string} title
 * @property {number} level
 * @property {number} startLine
 * @property {ParagraphPrint[]} paragraphs
 * @property {string[]} blockKinds
 * @property {Set<string>} topics
 * @property {boolean} isIntro
 */

/**
 * @typedef {object} DocumentPrint
 * @property {string | null} path
 * @property {Record<string, string>} frontmatter
 * @property {import("../document/model.js").Block[]} blocks
 * @property {SentencePrint[]} sentences
 * @property {ParagraphPrint[]} paragraphs
 * @property {SectionPrint[]} sections
 * @property {[number, string, number][]} headings (레벨, 제목, 줄)
 * @property {number} wordCount
 * @property {number} questionCount
 * @property {number} readerCallCount
 * @property {[number, string, number, string][]} countPromises (수, 단위, 줄, 원문)
 * @property {[number, string][]} promises
 * @property {[number, string][]} recalls
 * @property {[string, number, number][]} disabled
 * @property {SectionPrint} intro
 * @property {SectionPrint[]} bodySections
 */

/**
 * @param {string} text
 * @param {number} index
 * @param {number} line
 * @param {import("../document/model.js").Block} block
 * @param {number} paragraphIndex
 * @param {number} sectionIndex
 * @param {import("../analysis/index.js").Analyzer} analyzer
 * @param {import("./dictionaries.js").Entry[]} entries
 * @returns {SentencePrint}
 */
function makeSentencePrint(text, index, line, block, paragraphIndex, sectionIndex, analyzer, entries) {
  const ending = markers.endingOf(text);
  return {
    index,
    line,
    text,
    blockIndex: block.index,
    paragraphIndex,
    sectionIndex,
    length: wordCount(text),
    ending,
    mood: markers.moodOf(text, ending),
    commas: markers.countCommas(text),
    connectorStart: markers.connectorStartOf(text),
    causal: markers.countMatches(text, "causalMarkers.txt"),
    deixis: markers.matchedTexts(text, "deixis.txt"),
    euiCount: analyzer.euiCount(text),
    nounRun: analyzer.longestNounRun(text),
    passives: analyzer.doublePassives(text),
    hedges: markers.countMatches(text, "hedges.txt"),
    numbers: markers.countNumbers(text),
    topics: topicsOf(text),
    promises: markers.matchedTexts(text, "promiseMarkers.txt"),
    recalls: markers.matchedTexts(text, "recallMarkers.txt"),
    countPromises: markers.countPromisesIn(text),
    readerCall: markers.matchedTexts(text, "readerCalls.txt").length > 0,
    matches: matchesIn(text, entries),
  };
}

/**
 * @param {SentencePrint[]} sentences
 * @param {number} index
 * @param {import("../document/model.js").Block} block
 * @param {number} sectionIndex
 * @param {ParagraphPrint | null} previous
 * @param {boolean} followsProseDirectly
 * @returns {ParagraphPrint}
 */
function makeParagraphPrint(sentences, index, block, sectionIndex, previous, followsProseDirectly) {
  const lengths = sentences.map((s) => s.length);
  const topics = unionOf(sentences.map((s) => s.topics));
  return {
    index,
    blockIndex: block.index,
    sectionIndex,
    startLine: block.startLine,
    endLine: block.endLine,
    sentences,
    sentenceCount: sentences.length,
    meanLength: lengths.length ? mean(lengths) : 0,
    lengthStd: lengths.length > 1 ? pstdev(lengths) : 0,
    causalTotal: sentences.reduce((sum, s) => sum + s.causal, 0),
    deixisTotal: sentences.reduce((sum, s) => sum + s.deixis.length, 0),
    topics,
    overlapWithPrevious: previous ? overlap(previous.topics, topics) : null,
    followsProseDirectly,
    text: sentences.map((s) => s.text).join(" "),
  };
}

/**
 * @param {import("../document/model.js").Section} section
 * @param {number} sectionIndex
 * @param {import("../analysis/index.js").Analyzer} analyzer
 * @param {import("./dictionaries.js").Entry[]} entries
 * @param {SentencePrint[]} sentences
 * @param {ParagraphPrint[]} paragraphs
 * @returns {SectionPrint}
 */
function buildSection(section, sectionIndex, analyzer, entries, sentences, paragraphs) {
  /** @type {ParagraphPrint[]} */
  const sectionParagraphs = [];
  /** @type {import("../document/model.js").Block | null} */
  let previousBlock = null;
  for (const block of section.blocks) {
    if (block.kind !== PROSE) {
      previousBlock = block;
      continue;
    }
    const text = plainText(block.text);
    /** @type {SentencePrint[]} */
    const blockSentences = [];
    for (const sentence of analyzer.sentences(text)) {
      const line = block.startLine + countIn(text, "\n", sentence.start);
      const index = sentences.length + blockSentences.length;
      blockSentences.push(
        makeSentencePrint(sentence.text, index, line, block, paragraphs.length, sectionIndex, analyzer, entries),
      );
    }
    sentences.push(...blockSentences);
    const previous = sectionParagraphs.length ? sectionParagraphs[sectionParagraphs.length - 1] : null;
    const paragraph = makeParagraphPrint(
      blockSentences,
      paragraphs.length,
      block,
      sectionIndex,
      previous,
      previousBlock !== null && previousBlock.kind === PROSE,
    );
    paragraphs.push(paragraph);
    sectionParagraphs.push(paragraph);
    previousBlock = block;
  }
  const level = section.heading ? section.heading.level : 0;
  return {
    index: sectionIndex,
    title: sectionTitle(section),
    level,
    startLine: sectionStartLine(section),
    paragraphs: sectionParagraphs,
    blockKinds: section.blocks.map((b) => b.kind),
    topics: unionOf(sectionParagraphs.map((p) => p.topics)),
    isIntro: level === 0,
  };
}

/**
 * @param {import("../document/model.js").Document} doc
 * @param {import("../analysis/index.js").Analyzer} analyzer
 * @param {import("../config/settings.js").Config} [config]
 * @returns {DocumentPrint}
 */
export function buildFingerprint(doc, analyzer, config = defaultConfig()) {
  const entries = entriesFor(config);
  /** @type {SentencePrint[]} */
  const sentences = [];
  /** @type {ParagraphPrint[]} */
  const paragraphs = [];
  const sections = doc.sections.map((section, index) =>
    buildSection(section, index, analyzer, entries, sentences, paragraphs),
  );
  const headingBlocks = doc.blocks.filter((b) => b.kind === HEADING);
  /** @type {[number, string, number][]} */
  const headings = headingBlocks.map((b) => [b.level, b.text, b.startLine]);
  const headingQuestions = headingBlocks.filter((b) => b.text.includes("?")).length;
  return {
    path: doc.path,
    frontmatter: { ...doc.frontmatter },
    blocks: doc.blocks,
    sentences,
    paragraphs,
    sections,
    headings,
    wordCount: sentences.reduce((sum, s) => sum + s.length, 0),
    questionCount: sentences.filter((s) => s.mood === "의문").length + headingQuestions,
    readerCallCount: sentences.filter((s) => s.readerCall || s.mood === "명령").length,
    countPromises: sentences.flatMap((s) => s.countPromises.map(([n, unit, text]) => [n, unit, s.line, text])),
    promises: sentences.flatMap((s) => s.promises.map((text) => [s.line, text])),
    recalls: sentences.flatMap((s) => s.recalls.map((text) => [s.line, text])),
    disabled: doc.disabled,
    intro: sections[0],
    bodySections: sections.filter((s) => !s.isIntro),
  };
}
