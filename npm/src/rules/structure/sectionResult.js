// @ts-check
import { CODE, EMBED, IMAGE, TABLE } from "../../document/model.js";
import { NOTICE, SECTION, finding } from "../finding.js";

export const name = "sectionResult";
const RESULT_KINDS = [CODE, EMBED, IMAGE, TABLE];
const FILE_NAME = /[\w가-힣-]+\.(?:csv|xlsx|xls|parquet|json|png|jpg|svg|db|sqlite|txt|py|pdf|html|md)\b/;
const OUTPUT_WORDS = ["출력", "화면에", "찍힙니다", "나옵니다", "뜹니다", "보입니다", "만들어집니다", "생깁니다", "저장됩니다"];

/** @param {import("../../fingerprint/build.js").SectionPrint} section */
function leavesResult(section) {
  if (section.blockKinds.some((kind) => RESULT_KINDS.includes(kind))) return true;
  for (const paragraph of section.paragraphs) {
    for (const sentence of paragraph.sentences) {
      if (FILE_NAME.test(sentence.text) || OUTPUT_WORDS.some((word) => sentence.text.includes(word))) return true;
    }
  }
  return false;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  const body = doc.bodySections;
  body.forEach((section, index) => {
    if (index === body.length - 1) return;
    if (section.paragraphs.length <= config.sectionResultMinParagraphs) return;
    if (leavesResult(section)) return;
    findings.push(
      finding(name, section.startLine, section.title, "이 절에 독자가 확인할 결과 (코드, 표, 그림, 파일, 출력) 가 없다. 만들거나 확인할 것을 하나 넣는다", null, NOTICE, SECTION, section.index),
    );
  });
  return findings;
}
