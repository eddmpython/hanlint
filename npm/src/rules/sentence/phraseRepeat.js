// @ts-check
import { loadEntries } from "../../data/load.js";
import { compile } from "../../regex.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "phraseRepeat";
export const mechanism = "repeat";

/** 산문 문장이 이 수보다 적으면 비율이 튄다. 뜻은 파이썬 rules/sentence/phraseRepeat.py 가 소유한다. */
const MIN_SENTENCES = 8;
/** 되풀이로 세려면 몇 번 나와야 하는가. 한 번은 버릇이 아니다. */
const MIN_HITS = 2;

/** @returns {{pattern: import("../../regex.js").Pattern, share: number, label: string, why: string, source: string}[]} */
function entries() {
  return loadEntries("phraseRepeat.json").map((one) => ({
    pattern: compile(String(one.pattern)),
    share: Number(one.share),
    label: String(one.label),
    why: String(one.why),
    source: String(one.source),
  }));
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  void config;
  const findings = [];
  const prose = doc.sentences.filter((one) => one.length > 0 && one.ending !== "없음");
  if (prose.length < MIN_SENTENCES) return findings;
  for (const { pattern, share, label, why, source } of entries()) {
    const hit = prose.filter((one) => pattern.search(one.text) !== null);
    if (hit.length < MIN_HITS || hit.length / prose.length <= share) continue;
    const share100 = `${Math.round(share * 100)}%`;
    findings.push(
      finding(
        name,
        hit[0].line,
        hit[0].text,
        `\`${label}\` 꼴이 산문 ${prose.length}문장 가운데 ${hit.length}번이다 (상한 ${share100}). ${why} (${source})`,
        null,
        NOTICE,
        DOCUMENT,
        -1,
      ),
    );
  }
  return findings;
}
