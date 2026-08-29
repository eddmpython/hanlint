// @ts-check
import { PROSE } from "../../document/model.js";
import { NOTICE, SECTION, finding } from "../finding.js";

export const name = "blockUnread";
export const mechanism = "threshold";
const OUTPUT_LANGUAGES = ["", "text", "output", "console"];

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  void config;
  /** @type {Map<number, string>} */
  const languages = new Map(doc.codeBlocks.map((block) => [block.index, block.language]));
  const outputs = new Set([...languages].filter(([, language]) => OUTPUT_LANGUAGES.includes(language)).map(([index]) => index));
  if (!outputs.size) return [];
  const blocks = [...doc.blocks].sort((a, b) => a.index - b.index);
  const findings = [];
  for (let position = 0; position < blocks.length; position += 1) {
    const block = blocks[position];
    if (!outputs.has(block.index) || position === 0) continue;
    const previous = languages.get(blocks[position - 1].index);
    if (previous === undefined || OUTPUT_LANGUAGES.includes(previous)) continue;
    const following = position + 1 < blocks.length ? blocks[position + 1] : null;
    if (following !== null && following.kind === PROSE) continue;
    findings.push(
      finding(name, block.startLine, block.text.includes("\n") ? block.text.split("\n")[1] : block.text, "출력을 붙여 놓고 읽어 주지 않았다. 어느 부분이 무엇인지 짚는 문장을 바로 아래에 붙인다", null, NOTICE, SECTION, block.index),
    );
  }
  return findings;
}
