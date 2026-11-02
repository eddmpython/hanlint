// @ts-check
/** 사전 규칙의 공통 구현. cliche, translationese, redundantPair, japaneseLoan 이 사전 이름만 바꿔 쓴다. */
import { fitJosa } from "../../analysis/grammar/josa.js";
import { conventional, usageKindOf } from "../../usage/counts.js";
import { ERROR, SENTENCE, finding } from "../finding.js";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {string} dictionary
 * @param {string} ruleName
 * @param {string} [severity]
 * @returns {import("../finding.js").Finding[]}
 */
/** 문장 시작부터 걸린 자리까지의 줄바꿈 수. 뜻은 파이썬 rules/shared/dictionaryRule.py 가 소유한다. @param {string} text */
function countNewlines(text) {
  let count = 0;
  for (const ch of text) if (ch === "\n") count += 1;
  return count;
}

/** 사전 항목의 candidates가 지적의 후보로 나갈 때 붙는 까닭이다. 뜻은 파이썬 rules/shared/dictionaryRule.py 의 CANDIDATE_WHY 가 소유한다. */
const CANDIDATE_WHY = "사전 항목이 뜻에 따라 쓸 말로 적은 후보";

/**
 * 사전이 보는 글. 문단의 문장 뒤에 목록·표·제목·그림 설명 줄(fragments)이 온다. 뜻은 파이썬 rules/shared/dictionaryRule.py 의 units 가 소유한다.
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 */
function units(doc) {
  return [...doc.sentences, ...(doc.fragments ?? [])];
}

/** 사전 지적의 글. 찾은 말 뒤에 받침에 맞는 은/는을 붙인다. 뜻은 파이썬 rules/shared/dictionaryRule.py 의 message 가 소유한다.
 * @param {import("../../fingerprint/dictionaries.js").DictionaryMatch} match */
function message(match) {
  const source = match.source ? ` (${match.source})` : "";
  return `\`${match.text}\`${fitJosa(match.text, "는")} ${match.why}${source}`;
}

/**
 * @param {import("../../fingerprint/build.js").SentencePrint} sentence
 * @param {import("../../fingerprint/dictionaries.js").DictionaryMatch} match
 * @param {string} ruleName
 * @param {string} severity
 */
function matchFinding(sentence, match, ruleName, severity) {
  // 낱말만 갈아 끼우면 뒤에 붙은 조사가 틀어진다. `이슈로` 를 `쟁점로` 로 내밀던 자리다
  const tail = sentence.text.slice(match.end);
  const fix = match.fix !== null ? sentence.text.slice(0, match.start) + match.fix + fitJosa(match.fix, tail) : null;
  return finding(
    ruleName,
    sentence.line + countNewlines(sentence.text.slice(0, match.start)),
    sentence.text,
    message(match),
    fix,
    severity,
    SENTENCE,
    sentence.index,
    match.fix !== null ? match.text : null,
    match.fix,
    (match.candidates ?? []).map((text) => ({ text, why: CANDIDATE_WHY })),
  );
}

/**
 * 사전의 매치를 지적으로. config 를 주면 그 종류의 관용 항목 (usage.conventional) 은 넘긴다. 뜻은 파이썬
 * rules/shared/dictionaryRule.py 의 dictionaryFindings 가 소유한다.
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {string} dictionary
 * @param {string} ruleName
 * @param {string} [severity]
 * @param {import("../../config/settings.js").Config | null} [config]
 * @returns {import("../finding.js").Finding[]}
 */
export function dictionaryFindings(doc, dictionary, ruleName, severity = ERROR, config = null) {
  const findings = [];
  const kind = config ? usageKindOf(config) : null;
  for (const sentence of units(doc)) {
    for (const match of sentence.matches) {
      if (match.dictionary !== dictionary) continue;
      if (kind && config && conventional(dictionary, match.pattern, kind, config.usageShare)) continue;
      findings.push(matchFinding(sentence, match, ruleName, severity));
    }
  }
  return findings;
}

/**
 * 같은 자리에 항목이 둘이면 뒤의 것 (설정) 이 이긴다. 뜻은 파이썬 rules/shared/dictionaryRule.py 의 overridingFindings 가 소유한다.
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {string} dictionary
 * @param {string} ruleName
 * @param {string} [severity]
 * @param {string | null} [builtinSeverity]
 * @returns {import("../finding.js").Finding[]}
 */
export function overridingFindings(doc, dictionary, ruleName, severity = ERROR, builtinSeverity = null) {
  const findings = [];
  for (const sentence of units(doc)) {
    /** @type {Map<string, import("../../fingerprint/dictionaries.js").DictionaryMatch>} */
    const chosen = new Map();
    for (const match of sentence.matches) {
      if (match.dictionary === dictionary) chosen.set(`${match.start}:${match.end}`, match);
    }
    for (const match of [...chosen.values()].sort((a, b) => a.start - b.start)) findings.push(matchFinding(sentence, match, ruleName, match.pattern && builtinSeverity ? builtinSeverity : severity));
  }
  return findings;
}

/**
 * 문장마다 가장 앞의 매치 하나만 지적한다. 뜻은 파이썬 rules/shared/dictionaryRule.py 의 firstMatchFindings 가 소유한다.
 * 구체 무늬와 종결어미가 한 사전에 같이 사는 화면 사전에 쓴다. 항목에 to 규칙이 있으면 문장 전체를 낱말로 다시 쓴
 * 제안을 fix 로 낸다 (진행, 실패, 요구, 완료). 뜻을 골라야 하는 일반 종결어미는 to 가 없어 fix 도 없다.
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {string} dictionary
 * @param {string} ruleName
 * @param {string} [severity]
 * @returns {import("../finding.js").Finding[]}
 */
export function firstMatchFindings(doc, dictionary, ruleName, severity = ERROR) {
  const findings = [];
  for (const sentence of units(doc)) {
    const match = sentence.matches.find((m) => m.dictionary === dictionary);
    if (!match) continue;
    const [fragment, replacement] = match.rewrite ? changedSpan(sentence.text, match.rewrite) : [null, null];
    findings.push(
      finding(
        ruleName,
        sentence.line + countNewlines(sentence.text.slice(0, match.start)),
        sentence.text,
        message(match),
        match.rewrite,
        severity,
        SENTENCE,
        sentence.index,
        fragment,
        replacement,
      ),
    );
  }
  return findings;
}

/**
 * 두 글의 공통 앞뒤를 뺀 바뀐 조각. 편집기의 `이대로 고치기` 가 이 조각만 바꾼다. 뜻은 파이썬 changedSpan 이 소유한다.
 * @param {string} before @param {string} after @returns {[string, string]}
 */
export function changedSpan(before, after) {
  let head = 0;
  while (head < Math.min(before.length, after.length) && before[head] === after[head]) head++;
  let tail = 0;
  while (tail < Math.min(before.length, after.length) - head && before[before.length - 1 - tail] === after[after.length - 1 - tail]) tail++;
  return [before.slice(head, before.length - tail), after.slice(head, after.length - tail)];
}
