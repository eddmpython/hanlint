// @ts-check
import { overridingFindings } from "../shared/dictionaryRule.js";
import { NOTICE } from "../finding.js";

export const name = "calqueFrame";
export const mechanism = "dictionary";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return overridingFindings(doc, "calqueFrame", name, undefined, NOTICE);
}
