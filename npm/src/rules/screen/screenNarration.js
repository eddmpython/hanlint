// @ts-check
import { firstMatchFindings } from "../shared/dictionaryRule.js";

export const name = "screenNarration";
export const mechanism = "dictionary";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return firstMatchFindings(doc, "screenNarration", name);
}
