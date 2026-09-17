// @ts-check
/** 개인 원고와 승인을 분리한 휴대 가능한 기록. */
export const STORAGE_KEY = "hanlint.workspace.v1";
export function storageKeyFor(path) {
  const folder = path.endsWith("/") ? path : path.slice(0, path.lastIndexOf("/") + 1);
  return `${STORAGE_KEY}:${folder}`;
}
export const MAX_TEXT = 60000;
export const MAX_ARCHIVE_BYTES = 900000;
export const PRESETS = ["blog", "docs", "report", "guide", "essay", "fiction", "encyclopedia", "chat", "screen"];
const MAX_RECORDS = 100;

function textField(value, name, maximum = MAX_TEXT) {
  if (typeof value !== "string" || value.length > maximum) throw new Error(`${name} 형식을 확인해 주세요.`);
  return value;
}

export function newDraft(text = "", title = "새 원고", preset = "blog") {
  return { id: crypto.randomUUID(), title, text, original: text, preset, updatedAt: new Date().toISOString() };
}

export function emptyWorkspace(draft) {
  return { kind: "hanlint.workspace", version: 1, draft, records: [], patches: [], feedback: [] };
}

function checkedDraft(value) {
  if (!value || !PRESETS.includes(value.preset)) throw new Error("지원하는 글 종류의 원고가 아닙니다.");
  return { id: textField(value.id, "원고 ID", 100), title: textField(value.title, "원고 이름", 100),
    text: textField(value.text, "원고"), original: textField(value.original, "원문"), preset: value.preset,
    updatedAt: textField(value.updatedAt, "수정 시각", 40) };
}

export function parseWorkspace(text) {
  if (new TextEncoder().encode(text).length > MAX_ARCHIVE_BYTES) throw new Error("기록 파일이 너무 큽니다. 900 KB 이하 파일을 사용해 주세요.");
  const value = JSON.parse(text);
  if (value?.kind !== "hanlint.workspace" || value.version !== 1) throw new Error("한린트 기록 파일(version 1)이 아닙니다.");
  for (const key of ["records", "patches", "feedback"]) {
    if (!Array.isArray(value[key]) || value[key].length > 1000) throw new Error(`기록의 ${key} 형식을 확인해 주세요.`);
  }
  if (value.records.length > MAX_RECORDS) throw new Error("수정본은 기록 파일 하나에 100개까지 보관합니다.");
  const records = value.records.map((record) => ({ ...checkedDraft(record),
    recordId: textField(record.recordId, "기록 ID", 100), engineVersion: textField(record.engineVersion, "검사 버전", 50),
    reason: textField(record.reason, "수정 이유", 1000), origin: ["human", "assisted", "unspecified"].includes(record.origin) ? record.origin : "unspecified" }));
  const patches = value.patches.map((patch) => {
    const item = {};
    for (const key of ["rule", "before", "after", "moved", "sourceText", "sentence", "cue", "reader"]) item[key] = textField(patch[key], `고침 ${key}`);
    if (!Array.isArray(patch.presets) || !patch.presets.length || !patch.presets.every((preset) => PRESETS.includes(preset))) throw new Error("고침의 글 종류를 확인해 주세요.");
    item.presets = [...patch.presets];
    return item;
  });
  const feedback = value.feedback.map((item) => ({ rule: textField(item.rule, "지적 규칙", 100),
    quote: textField(item.quote, "지적 원문"), why: textField(item.why, "지적 이유", 2000),
    preset: textField(item.preset, "글 종류", 30), judgment: textField(item.judgment, "사용자 판단", 100),
    engineVersion: textField(item.engineVersion, "검사 버전", 50), at: textField(item.at, "판단 시각", 40) }));
  return { kind: "hanlint.workspace", version: 1, draft: checkedDraft(value.draft), records, patches, feedback };
}

export function serializeWorkspace(workspace) {
  const text = JSON.stringify(workspace, null, 2);
  return JSON.stringify(parseWorkspace(text), null, 2) + "\n";
}

export function addRecord(workspace, engineVersion, reason = "", origin = "unspecified") {
  const previous = workspace.records.at(-1), draft = workspace.draft;
  if (previous && previous.id === draft.id && previous.text === draft.text && previous.original === draft.original && previous.preset === draft.preset && previous.title === draft.title) return false;
  if (workspace.records.length >= MAX_RECORDS) throw new Error("수정본 100개가 모였습니다. 기록을 내보내고 이전 기록을 정리해 주세요.");
  workspace.records.push({ ...draft, recordId: crypto.randomUUID(), engineVersion, reason, origin });
  return true;
}

export function contribution(record, judgment) {
  return { kind: "hanlint.contribution", version: 1, engineVersion: record.engineVersion,
    preset: record.preset, before: record.original, after: record.text,
    reason: record.reason, origin: record.origin, judgment,
    meaning: "작성자가 선택한 사례이며 공통 규칙이나 품질 정답으로 승인되지 않았습니다." };
}
