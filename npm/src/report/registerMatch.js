// @ts-check
/** 한 문체로 저장한 본보기와 문형을 검사한 글의 문체에 맞춘다. */
import { HAPNIDA, REGISTERS, convertTemplate } from "../analysis/grammar/index.js";

/** 섞임과 없음은 데이터 정본의 합니다체를 유지한다. @param {string | null | undefined} register */
export function targetRegister(register) {
  return register && REGISTERS.includes(register) ? register : HAPNIDA;
}

/** @param {import("../data/exemplars.js").Exemplar} exemplar @param {string | null | undefined} register */
export function exemplarInRegister(exemplar, register) {
  const target = targetRegister(register);
  const before = convertTemplate(exemplar.before, target);
  const after = convertTemplate(exemplar.after, target);
  if (before.skipped || after.skipped) {
    throw new Error(
      exemplar.rule + " 본보기의 서술어를 못 풀었다: " + (before.skipped + after.skipped),
    );
  }
  return { rule: exemplar.rule, before: before.text, after: after.text, moved: exemplar.moved, presets: exemplar.presets };
}

/** @param {import("../data/patterns.js").Pattern} pattern @param {string | null | undefined} register */
export function patternInRegister(pattern, register) {
  const target = targetRegister(register);
  const form = convertTemplate(pattern.form, target);
  const example = convertTemplate(pattern.example, target);
  const instead = convertTemplate(pattern.instead, target);
  const skipped = form.skipped + example.skipped + instead.skipped;
  if (skipped) throw new Error(pattern.name + " 문형의 서술어를 못 풀었다: " + skipped);
  return {
    name: pattern.name,
    form: form.text,
    when: pattern.when,
    example: example.text,
    instead: instead.text,
    avoids: pattern.avoids,
    source: pattern.source,
  };
}
