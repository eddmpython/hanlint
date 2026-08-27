// @ts-check
import { NOTICE } from "../finding.js";
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "hardWord";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return dictionaryFindings(doc, "easyWords", name, NOTICE);
}
