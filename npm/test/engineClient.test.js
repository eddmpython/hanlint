import test from "node:test";
import assert from "node:assert/strict";
import { EngineClient } from "../../web/engineClient.js";

function fakeWorker() { return { sent: [], postMessage(message) { this.sent.push(message); }, terminate() { this.terminated = true; } }; }
test("모듈 자료가 준비되기 전 첫 검사 요청을 잃지 않는다", async () => {
  const worker = fakeWorker(), engine = new EngineClient(worker, () => {});
  const result = engine.request({ action: "analyze", text: "원고" });
  assert.equal(worker.sent.length, 0);
  worker.onmessage({ data: { ready: true } });
  assert.equal(worker.sent.length, 1);
  worker.onmessage({ data: { id: worker.sent[0].id, result: { findings: [] } } });
  assert.deepEqual(await result, { findings: [] });
  assert.equal(engine.pending.size, 0);
});
test("작업 로딩 실패와 시간 초과는 기다리는 모든 요청을 끝낸다", async () => {
  const worker = fakeWorker(), errors = [], engine = new EngineClient(worker, (error) => errors.push(error), 20);
  await assert.rejects(engine.request({ action: "analyze" }), /중단/);
  assert.equal(engine.pending.size, 0);
  assert.equal(worker.terminated, true);
  await assert.rejects(engine.request({ action: "analyze" }), /중단/);
  assert.equal(errors.length, 1);
});
