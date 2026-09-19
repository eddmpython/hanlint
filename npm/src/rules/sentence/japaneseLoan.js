// @ts-check
import { ERROR } from "../finding.js";
import { dictionaryFindings } from "../shared/dictionaryRule.js";

export const name = "japaneseLoan";
export const mechanism = "dictionary";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  return dictionaryFindings(doc, "japaneseLoan", name, ERROR, config);
}
