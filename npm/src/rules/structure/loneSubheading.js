// @ts-check
import { topicsOf } from "../../fingerprint/topics.js";
import { NOTICE, SECTION, finding } from "../finding.js";

export const name = "loneSubheading";
export const mechanism = "contrast";

/** (부모 H2 제목, 외동 H3 제목, 그 줄). H2 하나 아래 H3 이 정확히 하나일 때만. @param {[number, string, number][]} headings */
function onlyChild(headings) {
  /** @type {[string, string, number][]} */
  const found = [];
  for (let position = 0; position < headings.length; position += 1) {
    const [level, text] = headings[position];
    if (level !== 2) continue;
    /** @type {[string, number][]} */
    const children = [];
    for (const [childLevel, childText, childLine] of headings.slice(position + 1)) {
      if (childLevel <= 2) break;
      if (childLevel === 3) children.push([childText, childLine]);
    }
    if (children.length === 1) found.push([text, children[0][0], children[0][1]]);
  }
  return found;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  void config;
  const findings = [];
  for (const [parent, child, line] of onlyChild(doc.headings)) {
    const childTopics = topicsOf(child);
    const parentTopics = topicsOf(parent);
    if (!childTopics.size || ![...childTopics].every((word) => parentTopics.has(word))) continue;
    findings.push(
      finding(name, line, child, `\`${parent}\` 아래 소제목이 이것 하나뿐이고 절 제목에 없는 말이 하나도 없다. 소제목을 지우고 본문을 올린다`, null, NOTICE, SECTION, -1),
    );
  }
  return findings;
}
