// @ts-check
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "spelling";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return dictionaryFindings(doc, "spelling", name);
}
