// @ts-check
/**
 * 코드 블록을 언어와 본문으로 나눈다. 지문이 한 번 만들고 (DocumentPrint.codeBlocks) code 부류 규칙과 독자 상태가
 * 읽는다. 파이썬 fingerprint/codeBlocks.py 와 같다.
 * 펜스 첫 줄의 언어 표기 (```python) 를 읽고 본문 줄에 원문 줄 번호를 붙인다. text 펜스는 출력이다.
 */
import { CODE } from "../document/model.js";
import { fenceLanguage } from "../document/parseMarkdown.js";

const CLOSING_FENCE = /^\s*(?:```|~~~)\s*$/;

/**
 * @typedef {object} CodeBlock
 * @property {number} index
 * @property {number} startLine
 * @property {string} language
 * @property {[number, string][]} lines (원문 줄 번호, 코드 줄)
 * @property {string} text
 * @property {boolean} isOutput
 */

/** @param {import("../document/model.js").Block[]} blocks @returns {CodeBlock[]} */
export function codeBlocksOf(blocks) {
  /** @type {CodeBlock[]} */
  const found = [];
  for (const block of blocks) {
    if (block.kind !== CODE) continue;
    const raw = block.text.split("\n");
    const language = fenceLanguage(block.text);
    let body = raw.slice(1);
    if (body.length && CLOSING_FENCE.test(body[body.length - 1])) body = body.slice(0, -1);
    /** @type {[number, string][]} */
    const lines = body.map((line, offset) => [block.startLine + 1 + offset, line]);
    found.push({
      index: block.index,
      startLine: block.startLine,
      language,
      lines,
      text: lines.map(([, line]) => line).join("\n"),
      isOutput: ["text", "", "output", "console"].includes(language),
    });
  }
  return found;
}
