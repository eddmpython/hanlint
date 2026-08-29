// @ts-check
import { IMAGE } from "../../document/model.js";
import { SECTION, finding } from "../finding.js";

export const name = "introImage";
export const mechanism = "threshold";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  if (!doc.bodySections.length) return [];
  const count = doc.intro.blockKinds.filter((kind) => kind === IMAGE).length;
  if (count <= config.introMaxImages) return [];
  return [
    finding(name, doc.intro.startLine, doc.intro.title || "도입", `도입에 그림이 ${count}장이다. ${config.introMaxImages}장을 넘지 않는다. 나머지는 그것을 설명하는 절로 내린다`, null, "error", SECTION, doc.intro.index),
  ];
}
