// @ts-check
import { loadLines } from "../../data/load.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "platformApi";
export const mechanism = "dictionary";

/** @type {[RegExp, string, string][] | null} */
let cache = null;
function platformApis() {
  if (!cache) {
    cache = loadLines("platformApis.txt").map((line) => {
      const [pattern, platform, alternative] = line.split("\t");
      return /** @type {[RegExp, string, string]} */ ([new RegExp(pattern), platform, alternative]);
    });
  }
  return cache;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const block of doc.codeBlocks) {
    if (block.isOutput) continue;
    for (const [line, code] of block.lines) {
      for (const [pattern, platform, alternative] of platformApis()) {
        pattern.lastIndex = 0;
        if (pattern.test(code)) {
          findings.push(finding(name, line, code.trim(), `\`${pattern.source}\` 은 ${platform} 전용이다. 다른 운영체제 독자는 여기서 멈춘다. ${alternative}`, null, NOTICE, DOCUMENT, block.index));
          break;
        }
      }
    }
  }
  return findings;
}
