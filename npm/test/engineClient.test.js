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
test("워커 하나만 받으면 시간 초과가 기다리는 모든 요청을 끝내고 멈춘다", async () => {
  const worker = fakeWorker(), errors = [], engine = new EngineClient(worker, (error) => errors.push(error), 20);
  await assert.rejects(engine.request({ action: "analyze" }), /중단/);
  assert.equal(engine.pending.size, 0);
  assert.equal(worker.terminated, true);
  await assert.rejects(engine.request({ action: "analyze" }), /중단/);
  assert.equal(errors.length, 1);
});
test("워커 공장을 받으면 시간 초과가 그 요청만 끝내고 워커를 새로 띄운다", async () => {
  const workers = [];
  const errors = [];
  const engine = new EngineClient(() => { const worker = fakeWorker(); workers.push(worker); return worker; }, (error) => errors.push(error), 20);
  assert.equal(workers.length, 1);
  await assert.rejects(engine.request({ action: "analyze" }), /다시 띄웠/);
  assert.equal(workers[0].terminated, true);
  assert.equal(workers.length, 2);
  assert.equal(errors.length, 1);
  const next = engine.request({ action: "analyze", text: "다시" });
  workers[1].onmessage({ data: { ready: true } });
  assert.equal(workers[1].sent.length, 1);
  workers[1].onmessage({ data: { id: workers[1].sent[0].id, result: { findings: [] } } });
  assert.deepEqual(await next, { findings: [] });
  // 옛 워커가 늦게 보낸 답은 무시한다
  workers[0].onmessage({ data: { id: 999, result: {} } });
  assert.equal(engine.pending.size, 0);
});
test("요청마다 제한을 달리 줄 수 있고 연달아 실패하면 멈춘다", async () => {
  const workers = [];
  const engine = new EngineClient(() => { const worker = fakeWorker(); workers.push(worker); return worker; }, () => {}, 5);
  const slow = engine.request({ action: "sheet" }, 200);
  workers[0].onmessage({ data: { ready: true } });
  workers[0].onmessage({ data: { id: workers[0].sent[0].id, result: [1] } });
  assert.deepEqual(await slow, [1]);
  for (let i = 0; i < 4; i++) await assert.rejects(engine.request({ action: "analyze" }), /중단/);
  assert.equal(workers.length, 4);
  await assert.rejects(engine.request({ action: "analyze" }), /중단/);
  assert.equal(workers.length, 4);
});
