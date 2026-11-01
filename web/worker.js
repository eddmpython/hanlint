// @ts-check
/** 편집 입력과 분리한 검사 작업. 배포 조립에서 같은 npm 공개 API를 나란히 둔다. */
import { inspectText, learnText, compareRevision, configFromMapping, applyFixes, verifyPatch, Contract, Patch, version, SOURCE_SUFFIXES, sheetRows, renderSheet, renderSheetJson, applyRows } from "./npm/src/index.js";

function analyze({ text, original, preset, patches }) {
  const config = configFromMapping({ preset, patches });
  const inspection = inspectText(text, config);
  return { ...inspection, protection: compareRevision(original, text, config), learned: learnText(original, text, config), version };
}

self.onmessage = ({ data }) => {
  try {
    const config = configFromMapping({ preset: data.preset, patches: data.patches });
    if (data.action === "analyze") self.postMessage({ id: data.id, result: analyze(data) });
    else if (data.action === "fix") {
      const inspection = inspectText(data.text, config);
      const selected = data.index === null ? inspection.findings.filter((item) => item.severity === "error") : [inspection.findings[data.index]].filter(Boolean);
      const fixed = applyFixes(data.text, selected);
      const protection = compareRevision(data.text, fixed.text, config);
      const before = inspection, after = inspectText(fixed.text, config);
      const newIssues = Object.values(protection.changes).some((values) => values.length) || protection.outline.mismatches.length;
      const beforeErrors = new Map();
      for (const finding of before.findings.filter((item) => item.severity === "error")) beforeErrors.set(finding.rule, (beforeErrors.get(finding.rule) ?? 0) + 1);
      const afterErrors = new Map();
      for (const finding of after.findings.filter((item) => item.severity === "error")) afterErrors.set(finding.rule, (afterErrors.get(finding.rule) ?? 0) + 1);
      if (newIssues || [...afterErrors].some(([rule, count]) => count > (beforeErrors.get(rule) ?? 0))) throw new Error("자동으로 고치면 숫자, 링크, 코드나 소제목 순서가 바뀌거나 새 지적이 생겨서 고치지 않았어요. 원고는 그대로 두었으니 직접 고쳐 주세요.");
      self.postMessage({ id: data.id, result: fixed });
    } else if (data.action === "patch") {
      const inspection = inspectText(data.text, config), finding = inspection.report.findings[data.index];
      if (!finding?.patch) throw new Error("이 문장에 맞는 기억한 고침이 없어요.");
      const patch = new Patch(finding.rule, finding.patch.before, finding.patch.after);
      const contract = new Contract("글쓴이", "원문을 다듬는다", [data.text.trim().normalize("NFC") || "원문"]);
      const result = verifyPatch(data.text, patch, contract, config);
      if (!result.verified) throw new Error("기억한 고침을 지금 이 문장에 적용할 수 없어요. 원고는 그대로 두었어요.");
      if (!compareRevision(data.text, result.resultText, config).outline.matches) throw new Error("기억한 고침이 소제목 순서를 바꿔서 적용하지 않았어요. 원고는 그대로 두었어요.");
      self.postMessage({ id: data.id, result: { text: result.resultText, applied: [finding.rule] } });
    } else if (data.action === "sourceSuffixes") self.postMessage({ id: data.id, result: { suffixes: SOURCE_SUFFIXES } });
    else if (data.action === "sheet") {
      // CLI의 `sheet --format json`과 같은 행. 같은 파일이면 같은 표가 나온다.
      const rows = sheetRows(data.files, config, Boolean(data.everything));
      self.postMessage({ id: data.id, result: JSON.parse(renderSheetJson(rows, config.preset, data.files.length)).rows });
    } else if (data.action === "sheetText") self.postMessage({ id: data.id, result: renderSheet(data.rows, config.preset, data.fileCount) });
    else if (data.action === "sheetApply") self.postMessage({ id: data.id, result: applyRows(data.source, data.rows) });
    else throw new Error("지원하지 않는 요청이에요.");
  } catch (error) { self.postMessage({ id: data.id, error: error.message }); }
};
self.postMessage({ ready: true });
