// @ts-check
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "translationese";
export const mechanism = "dictionary";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return dictionaryFindings(doc, "translationese", name);
}
