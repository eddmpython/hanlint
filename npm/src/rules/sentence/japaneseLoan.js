// @ts-check
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "japaneseLoan";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return dictionaryFindings(doc, "japaneseLoan", name);
}
