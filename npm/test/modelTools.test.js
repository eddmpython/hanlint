import test from "node:test";
import assert from "node:assert/strict";
import { registerEditorTools } from "../../web/modelTools.js";

test("편집 도구는 같은 동작을 부르고 잘못된 입력은 변경하지 않는다", async () => {
  const tools = new Map(); let text = "원문", count = 0, signal;
  const stop = registerEditorTools({ registerTool(tool, options) { tools.set(tool.name, tool); signal = options.signal; } }, {
    inspect: async () => ({ text }), replace: async (value) => { text = value; count++; return { text }; },
  }, () => assert.fail("등록 오류"));
  assert.equal(tools.get("inspectDraft").annotations.readOnlyHint, true);
  assert.deepEqual(await tools.get("setDraftText").execute({ text: "수정문" }), { text: "수정문" });
  assert.deepEqual(await tools.get("inspectDraft").execute({}), { text: "수정문" });
  assert.throws(() => tools.get("setDraftText").execute({ text: 1 }));
  assert.throws(() => tools.get("setDraftText").execute({ text: "a", token: "secret" }));
  assert.equal(count, 1);
  stop(); assert.equal(signal.aborted, true);
});
