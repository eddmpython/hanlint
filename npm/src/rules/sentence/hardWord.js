// @ts-check
import { NOTICE } from "../finding.js";
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "hardWord";
export const mechanism = "dictionary";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  return dictionaryFindings(doc, "easyWords", name, NOTICE, config);
}
