// @ts-check
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "spacing";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return dictionaryFindings(doc, "spacing", name);
}
