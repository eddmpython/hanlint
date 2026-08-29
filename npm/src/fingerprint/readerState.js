// @ts-check
/**
 * 독자 상태. 글을 위에서 아래로 읽는 독자가 어느 자리에서 무엇을 손에 들고 무엇을 이미 보았는가.
 * 파이썬 fingerprint/readerState.py 와 같다. reader 기제의 규칙은 어느 자리가 요구하는 것을 그 자리의 상태에
 * 대 본다. 상태는 블록과 문장 순서로 쌓이고 한 번 쌓은 것은 바뀌지 않는다. 집합은 고치지 않는다.
 */
import { CODE, PROSE } from "../document/model.js";
import { createdIn } from "./codeMarkers.js";
import { numeralsIn } from "./markers.js";

/**
 * 한 자리 (문장 하나 또는 블록 하나) 를 읽기 직전의 독자.
 * @typedef {object} ReaderState
 * @property {import("./build.js").SentencePrint | null} previous 바로 앞에 읽은 산문 문장
 * @property {Set<string>} recent 손에 든 화제어. 바로 앞 문장의 것이고 앞 문장이 없으면 빈 집합
 * @property {Set<string>} numerals 지금까지 산문과 블록에 나온 수 (천 단위 쉼표를 뗀 꼴)
 * @property {Set<string>} files 앞선 코드 블록이 만든 파일 이름과 폴더
 * @property {number} sentencesRead 지금까지 읽은 산문 문장 수
 * @property {[number, string][]} promises 지금까지 뒤로 미룬 표지 (줄, 원문)
 * @property {[number, string][]} recalls 지금까지 앞을 회수한 표지 (줄, 원문)
 */

/**
 * 자리마다의 독자 상태. 문장은 index 로, 블록은 index 로 찾는다.
 * @typedef {object} ReaderTrail
 * @property {ReaderState[]} beforeSentence
 * @property {ReaderState[]} beforeBlock
 * @property {ReaderState} final 글을 다 읽은 독자
 * @property {(blockIndex: number, name: string) => boolean} mentionedBefore 블록보다 앞선 산문이 그 이름을 불렀는가
 */

/** @type {Set<string>} */
const NOTHING = new Set();

/** @param {Set<string>} base @param {Set<string>} added */
function union(base, added) {
  if (!added.size) return base;
  const out = new Set(base);
  for (const value of added) out.add(value);
  return out;
}

/** @param {ReaderState} state @param {import("./build.js").SentencePrint} sentence @returns {ReaderState} */
function afterSentence(state, sentence) {
  return {
    previous: sentence,
    recent: sentence.topics,
    numerals: union(state.numerals, numeralsIn(sentence.text)),
    files: state.files,
    sentencesRead: state.sentencesRead + 1,
    promises: [...state.promises, ...sentence.promises.map((text) => /** @type {[number, string]} */ ([sentence.line, text]))],
    recalls: [...state.recalls, ...sentence.recalls.map((text) => /** @type {[number, string]} */ ([sentence.line, text]))],
  };
}

/**
 * 산문 아닌 블록을 지난 독자. 수는 어느 블록에서든 보고 파일은 코드 블록이 만든다.
 * @param {ReaderState} state
 * @param {import("../document/model.js").Block} block
 * @param {import("./codeBlocks.js").CodeBlock | undefined} code
 * @returns {ReaderState}
 */
function afterBlock(state, block, code) {
  let files = state.files;
  if (code) {
    const [made, dirs] = createdIn(code.lines.map(([, line]) => line));
    files = union(union(files, made), dirs);
  }
  return { ...state, numerals: union(state.numerals, numeralsIn(block.text)), files };
}

/**
 * 블록 순서로 한 번 지나며 자리마다의 상태를 적는다. 산문 블록은 문장 하나씩, 나머지는 블록째 읽는다.
 * @param {import("../document/model.js").Block[]} blocks
 * @param {import("./codeBlocks.js").CodeBlock[]} codeBlocks
 * @param {import("./build.js").SentencePrint[]} sentences
 * @returns {ReaderTrail}
 */
export function buildReaderTrail(blocks, codeBlocks, sentences) {
  const codeByIndex = new Map(codeBlocks.map((code) => [code.index, code]));
  /** @type {ReaderState[]} */
  const beforeSentence = [];
  /** @type {ReaderState[]} */
  const beforeBlock = [];
  /** @type {ReaderState} */
  let state = { previous: null, recent: NOTHING, numerals: NOTHING, files: NOTHING, sentencesRead: 0, promises: [], recalls: [] };
  let position = 0;
  for (const block of blocks) {
    beforeBlock.push(state);
    if (block.kind === PROSE) {
      while (position < sentences.length && sentences[position].blockIndex === block.index) {
        beforeSentence.push(state);
        state = afterSentence(state, sentences[position]);
        position += 1;
      }
    } else {
      state = afterBlock(state, block, block.kind === CODE ? codeByIndex.get(block.index) : undefined);
    }
  }
  if (position !== sentences.length) {
    throw new Error(`문장 ${sentences.length - position}개가 어느 블록에도 안 든다. 문장과 블록의 순서가 어긋났다`);
  }
  return {
    beforeSentence,
    beforeBlock,
    final: state,
    mentionedBefore(blockIndex, name) {
      const read = beforeBlock[blockIndex].sentencesRead;
      return sentences.slice(0, read).some((sentence) => sentence.text.includes(name));
    },
  };
}
