// @ts-check
import { overridingFindings } from "../shared/dictionaryRule.js";

export const name = "screenWord";
export const mechanism = "dictionary";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  return overridingFindings(doc, "screenWord", name);
}
