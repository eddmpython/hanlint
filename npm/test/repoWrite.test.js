// @ts-check
/** 브라우저에서 표의 고침을 GitHub 에 되돌려 쓰기. 가짜 fetch 와 실제 applyRows 로 파일 읽기, 바꾸기, commit 을 본다. 네트워크는 없다. */
import assert from "node:assert/strict";
import test from "node:test";

import { applyRows } from "../src/index.js";
import { GitHubStore } from "../../web/github.js";
import { RepoWriter } from "../../web/repoWrite.js";

const engine = { async request(payload) { assert.equal(payload.action, "sheetApply"); return applyRows(payload.source, payload.rows); } };
const encode = (text) => Buffer.from(text, "utf-8").toString("base64");
const decode = (content) => Buffer.from(content, "base64").toString("utf-8");
function reply(status, value = {}) { return { status, ok: status >= 200 && status < 300, json: async () => value }; }

test("writes each changed file once on the branch, keeps CRLF and reports failures per place", async () => {
  const calls = [];
  const files = { "src/a.js": "const A = '요청을 완료하지 못했습니다'\r\nconst B = '없음'\r\n", "src/b.js": "const C = '저장되지 않았습니다'\n" };
  const store = new GitHubStore(async (url, options) => {
    calls.push({ url, options });
    const path = decodeURIComponent(url.split("/contents/")[1].split("?")[0]);
    if (!options.method) return path in files ? reply(200, { type: "file", encoding: "base64", content: encode(files[path]), sha: `sha-${path}` }) : reply(404);
    const body = JSON.parse(options.body);
    files[path] = decode(body.content);
    return reply(200, { commit: { sha: `commit-${path}` }, content: { sha: "new" } });
  });
  const writer = new RepoWriter(engine, store);
  const progress = [];
  const rows = [
    { file: "src/a.js", line: 1, column: 12, text: "요청을 완료하지 못했습니다", fix: "요청 완료 실패" },
    { file: "src/a.js", line: 2, column: 12, text: "없음", fix: "" },
    { file: "src/b.js", line: 1, column: 12, text: "저장되지 않았습니다", fix: "저장 실패" },
    { file: "src/b.js", line: 9, column: 1, text: "글", fix: "고침" },
    { file: "src/gone.js", line: 1, column: 1, text: "글", fix: "고침" },
  ];
  const summary = await writer.write({ owner: "o", repo: "r", ref: "release/8.0" }, rows, "token", (done, total, file) => progress.push([done, total, file]));
  assert.equal(summary.applied, 2);
  assert.equal(summary.failed, 2);
  assert.deepEqual(summary.files.map((item) => [item.file, item.commit, item.failed]), [
    ["src/a.js", "commit-src/a.js", []],
    ["src/b.js", "commit-src/b.js", ["src/b.js:9:1: 그 줄이 없다"]],
    ["src/gone.js", null, ["src/gone.js: 파일이 없다"]],
  ]);
  assert.equal(files["src/a.js"], "const A = '요청 완료 실패'\r\nconst B = '없음'\r\n");
  assert.equal(files["src/b.js"], "const C = '저장 실패'\n");
  const put = calls.filter((call) => call.options.method === "PUT");
  assert.equal(put.length, 2);
  const body = JSON.parse(put[0].options.body);
  assert.deepEqual([body.branch, body.sha, body.message], ["release/8.0", "sha-src/a.js", "hanlint: 화면 글 고침 1곳 (src/a.js)"]);
  assert.ok(calls.every((call) => call.options.headers.Authorization === "Bearer token" && call.url.startsWith("https://api.github.com/repos/o/r/contents/")));
  assert.ok(calls[0].url.endsWith("?ref=release%2F8.0"));
  assert.deepEqual(progress, [[1, 3, "src/a.js"], [2, 3, "src/b.js"], [3, 3, "src/gone.js"]]);
  writer.forget();
  assert.equal(store.token, "");
});

test("rows without a fix write nothing and a bad token stops before any request", async () => {
  const calls = [];
  const writer = new RepoWriter(engine, new GitHubStore(async (url) => { calls.push(url); return reply(200); }));
  const empty = await writer.write({ owner: "o", repo: "r", ref: "main" }, [{ file: "a.js", line: 1, column: 1, text: "글", fix: "" }], "token");
  assert.deepEqual([empty.applied, empty.failed, calls.length], [0, 0, 0]);
  await assert.rejects(writer.write({ owner: "o", repo: "r", ref: "main" }, [], ""), /토큰/);
});
