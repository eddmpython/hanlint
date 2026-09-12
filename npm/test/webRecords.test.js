import test from "node:test";
import assert from "node:assert/strict";
import { GitHubStore } from "../../web/github.js";
import { newDraft, emptyWorkspace, parseWorkspace, serializeWorkspace, addRecord, contribution, storageKeyFor } from "../../web/records.js";

test("같은 배포 폴더는 기록을 공유하고 다른 Pages 경로와는 구분한다", () => {
  assert.equal(storageKeyFor("/hanlint/"), storageKeyFor("/hanlint/index.html"));
  assert.notEqual(storageKeyFor("/hanlint/"), storageKeyFor("/"));
  assert.notEqual(storageKeyFor("/hanlint/"), storageKeyFor("/myFork/"));
});

test("원고와 명시한 판단만 보관하고 인증 정보는 내보내지 않는다", () => {
  const workspace = emptyWorkspace(newDraft("결과입니다.", "한글 😀 원고"));
  workspace.token = "sensitive";
  workspace.draft.token = "sensitive";
  assert.equal(addRecord(workspace, "0.0.10", "관계를 풀어 씀", "human"), true);
  assert.equal(addRecord(workspace, "0.0.10"), false);
  const text = serializeWorkspace(workspace);
  assert.ok(!text.includes("sensitive"));
  const restored = parseWorkspace(text);
  assert.equal(restored.records[0].title, "한글 😀 원고");
  assert.equal(restored.records[0].origin, "human");
  assert.equal(restored.patches.length, 0);
  const sample = contribution(restored.records[0], "submittedForReview");
  assert.equal(sample.before, workspace.draft.original);
  assert.ok(!("token" in sample));
});

test("깨진 형식과 지원 밖 버전은 원고를 가져오기 전에 거부한다", () => {
  assert.throws(() => parseWorkspace('{"version":2}'));
  const workspace = emptyWorkspace(newDraft("text"));
  workspace.draft.text = { html: "<script>" };
  assert.throws(() => serializeWorkspace(workspace));
});

function reply(status, value = {}) { return { status, ok: status >= 200 && status < 300, json: async () => value }; }

test("GitHub는 처음 생성하고 확인한 SHA로만 갱신한다", async () => {
  const calls = [], workspace = emptyWorkspace(newDraft("원문 😀\n둘째 줄"));
  const replies = [reply(200, { private: true }), reply(404), reply(201, { content: { sha: "first", html_url: "https://github.com/me/writing" } }), reply(200, { content: { sha: "second" } })];
  const store = new GitHubStore(async (url, options) => { calls.push({ url, options }); return replies.shift(); });
  store.connect("me/writing", "test-token");
  await store.save(workspace);
  assert.equal(JSON.parse(calls[2].options.body).sha, undefined);
  const content = JSON.parse(calls[2].options.body).content;
  assert.equal(JSON.parse(Buffer.from(content, "base64").toString("utf8")).draft.text, workspace.draft.text);
  await store.save(workspace);
  assert.equal(JSON.parse(calls[3].options.body).sha, "first");
  assert.ok(calls.every((call) => call.url.startsWith("https://api.github.com/repos/me/writing")));
  assert.ok(calls.every((call) => !call.url.includes("test-token")));
  store.disconnect();
  assert.equal(store.token, "");
  assert.equal(store.sha, undefined);
});

test("기존 원격 기록은 먼저 가져와야 하며 충돌은 재전송하지 않는다", async () => {
  let count = 0;
  const store = new GitHubStore(async () => { count++; return reply(200, { sha: "existing" }); });
  store.connect("me/writing", "test-token");
  await assert.rejects(store.save(emptyWorkspace(newDraft("local"))), /기존 기록/);
  assert.equal(count, 2);
  store.accept("stale"); count = 0;
  store.request = async () => { count++; return reply(409); };
  await assert.rejects(store.save(emptyWorkspace(newDraft("local"))), /달라졌거나/);
  assert.equal(count, 1);
});

test("원격 파일을 검증한 뒤 명시적으로 수락해야 갱신 기준이 바뀐다", async () => {
  const workspace = emptyWorkspace(newDraft("한글"));
  const store = new GitHubStore(async () => reply(200, { type: "file", encoding: "base64", content: Buffer.from(serializeWorkspace(workspace)).toString("base64"), sha: "remote" }));
  store.connect("me/writing", "test-token");
  const loaded = await store.load();
  assert.equal(store.sha, undefined);
  assert.equal(loaded.workspace.draft.text, "한글");
  store.accept(loaded.sha);
  assert.equal(store.sha, "remote");
  assert.throws(() => store.connect("me/../else", "token"));
});
