// @ts-check
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "redundantPair";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return dictionaryFindings(doc, "redundantPair", name);
}
