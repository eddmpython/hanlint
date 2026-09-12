// @ts-check
/** 지원 브라우저에서 편집기와 같은 동작을 구조화 도구로 노출한다. */
import { MAX_TEXT } from "./records.js";

export function registerEditorTools(context, editor, onError) {
  if (!context?.registerTool) return () => {};
  const lifecycle = new AbortController();
  const tools = [
    { name: "inspectDraft", title: "현재 원고 검사", description: "현재 한린트 원고의 지적과 원문 보호 변화를 읽습니다. 원고나 기록을 변경하지 않습니다.",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      execute(input) {
        if (!input || typeof input !== "object" || Array.isArray(input) || Object.keys(input).length) throw new Error("검사에는 빈 객체를 전달해 주세요.");
        return editor.inspect();
      } },
    { name: "setDraftText", title: "현재 원고 편집", description: "현재 편집기의 원고를 교체하고 재검사합니다. 브라우저 임시 기록에 남고 되돌릴 수 있습니다. GitHub로 전송하지 않습니다.",
      inputSchema: { type: "object", properties: { text: { type: "string", maxLength: MAX_TEXT } }, required: ["text"], additionalProperties: false },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      execute(input) {
        if (!input || typeof input !== "object" || Array.isArray(input) || Object.keys(input).some((key) => key !== "text") || typeof input.text !== "string" || input.text.length > MAX_TEXT) throw new Error("60,000자 이하 text 문자열을 전달해 주세요.");
        return editor.replace(input.text);
      } },
  ];
  for (const tool of tools) {
    try { Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch(onError); }
    catch (error) { onError(error); }
  }
  return () => lifecycle.abort();
}
