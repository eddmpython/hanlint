/** 설치된 pyproc 공개 제어로 원문, 결과, 아래 수정본과 기록을 실측한다. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { storageKeyFor } from "../../web/records.js";

const require = createRequire(new URL("../../npm/package.json", import.meta.url));
const { PyProcControlClient } = await import(pathToFileURL(require.resolve("pyproc/control")));
const [config, output, url = "http://127.0.0.1:4179/"] = process.argv.slice(2);
if (!config || !output) throw new Error("node scripts/measure/site.mjs <manifest> <공통 실행 공간 출력> [URL]");
const storageKey = JSON.stringify(storageKeyFor(new URL(url).pathname));
await mkdir(output, { recursive: true });
const client = await PyProcControlClient.start(config);
let opened, attached;
try {
  async function open() {
    opened = await client.openTarget(url, { expectedRisk: "externalEffect", waitUntil: "load" });
    attached = await client.attachSession(opened.output.targetRef);
  }
  async function close() {
    await client.detachSession(attached.output); attached = null;
    await client.closeTarget(opened.output.targetRef); opened = null;
  }
  async function evaluate(expression) {
    const result = await client.command(attached.output, "Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }, { expectedRisk: "externalEffect" });
    if (result.output.result.exceptionDetails) throw new Error(JSON.stringify(result.output.result.exceptionDetails));
    return result.output.result.result.value;
  }
  async function waitFor(expression) {
    const matched = await evaluate(`new Promise(resolve => { const until = Date.now() + 25000; const timer = setInterval(() => { if (${expression}) {clearInterval(timer);resolve(true)} else if(Date.now() > until) {clearInterval(timer);resolve(false)} }, 80); })`);
    assert.equal(matched, true, expression);
  }
  async function click(name, role = "button") {
    await evaluate(`[...document.querySelectorAll('button,summary,[role=tab]')].find(node=>(node.getAttribute('aria-label')||node.textContent.replace(/[↗↙＋]/g,'').trim())===${JSON.stringify(name)})?.scrollIntoView({block:'center'})`);
    const observed = await client.observe(attached.output, { expectedRisk: "read", mode: "all", maxNodes: 500 });
    const page = observed.output.result ?? observed.output;
    assert.equal(page.inventory.complete, true);
    const matches = page.nodes.filter((node) => node.role === (role ?? "DisclosureTriangle") && node.name?.trim() === name);
    assert.equal(matches.length, 1, name);
    try {
      await client.act(attached.output, [{ kind: "click", locatorRef: matches[0].locatorRef, expectedRisk: "externalEffect" }]);
    } catch (error) { throw new Error(`${name}: ${error.message}`, { cause: error }); }
  }
  async function capture(name) {
    const captured = await client.act(attached.output, [{ kind: "screenshot", format: "png", expectedRisk: "read" }]);
    await writeFile(resolve(output, `${name}.png`), captured.attachments[0].bytes);
    await client.deleteArtifact(captured.output.actions[0].result.artifactRef);
  }
  async function enter(id, text, inputType = "insertText") {
    await evaluate(`document.getElementById(${JSON.stringify(id)}).value=${JSON.stringify(text)};document.getElementById(${JSON.stringify(id)}).dispatchEvent(new InputEvent('input',{bubbles:true,inputType:${JSON.stringify(inputType)}}))`);
    await waitFor("document.querySelector('#reviewSummary').textContent !== '수정한 문장을 다시 읽고 있어요.'");
  }
  await open();
  await waitFor("document.querySelector('#version').textContent.length > 0");
  await click("내 기록과 보관", null); await click("내 기록");
  await click("이 브라우저 기록 삭제"); await click("브라우저 기록 삭제");
  await click("예문");
  await close(); await open();
  await waitFor("document.querySelectorAll('.findingCard').length > 0");
  await evaluate("document.fonts.ready");
  const initial = await evaluate(`({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,channels:document.querySelectorAll('#channels a').length,text:document.querySelector('#sourceInput').value,revision:document.querySelector('#draft').value,count:Number(document.querySelector('#findingCount').textContent),cards:document.querySelectorAll('.findingCard').length,firstCard:document.querySelector('.findingCard').getBoundingClientRect().top,sourceLeft:document.querySelector('.inputPanel').getBoundingClientRect().left,resultLeft:document.querySelector('.resultPanel').getBoundingClientRect().left,gridBottom:document.querySelector('.workGrid').getBoundingClientRect().bottom,revisionTop:document.querySelector('#revisionSection').getBoundingClientRect().top,font:document.fonts.check('16px Pretendard'),advanced:document.querySelector('.revisionDetails').open,storage:document.querySelector('.workspaceTools').open})`);
  assert.equal(initial.overflow, false); assert.equal(initial.channels, 5); assert.equal(initial.font, true);
  assert.equal(initial.revision, ""); assert.equal(initial.advanced, false); assert.equal(initial.storage, false);
  assert.equal(initial.count, 3); assert.equal(initial.cards, 3);
  assert.ok(initial.revisionTop >= initial.gridBottom);
  if (initial.width > 760) assert.ok(initial.resultLeft > initial.sourceLeft);
  await capture("firstView");
  await click("결과가 저장되어집니다.", null);
  assert.equal(await evaluate("document.querySelectorAll('.findingCard[open]').length"), 1);
  await capture("finding");
  await click("수정본에 반영");
  await waitFor("document.querySelector('#draft').value.includes('결과가 저장됩니다.') && !document.querySelector('#saveButton').disabled");
  const fixed = await evaluate("document.querySelector('#draft').value");
  assert.notEqual(fixed, initial.text);
  assert.equal(await evaluate("document.querySelector('#sourceInput').value"), initial.text);
  assert.equal(await evaluate("document.querySelector('#sourceInput').readOnly"), true);
  assert.equal(await evaluate("document.querySelector('#resultOrigin').textContent"), "수정본");
  await click("되돌리기");
  await waitFor(`document.querySelector('#draft').value === ${JSON.stringify(initial.text)} && !document.querySelector('#fixAllButton').disabled`);
  await click("고칠 수 있는 곳 반영");
  await waitFor(`document.querySelector('#draft').value === ${JSON.stringify(fixed)} && !document.querySelector('#saveButton').disabled`);
  await click("전후 비교");
  assert.equal(await evaluate("document.querySelector('#originalPane').hidden"), false);
  await capture("revision");
  await click("수정본 기록"); await click("이 수정본 남기기");
  await waitFor(`JSON.parse(localStorage.getItem(${storageKey})).records.length === 1`);
  await click("원문 보호와 고침 기억", null);
  assert.ok((await evaluate("document.querySelector('#protection').innerText")).includes("변화 없음"));
  await click("고침 기억", "tab");
  await waitFor("document.querySelectorAll('#memory .memoryItem').length > 0");
  await click("doublePassive 3줄 고침 기억"); await click("내 고침으로 기억");
  await waitFor(`JSON.parse(localStorage.getItem(${storageKey})).patches.length === 1`);
  await capture("remember");
  await enter("draft", initial.text, "insertFromPaste");
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem(${storageKey})).draft.original`), initial.text);
  await click("결과가 저장되어집니다.", null); await click("기억한 고침 적용");
  await waitFor(`document.querySelector('#draft').value === ${JSON.stringify(fixed)} && !document.querySelector('#saveButton').disabled`);
  await click("내 기록과 보관", null); await click("내 기록");
  assert.equal(await evaluate("document.querySelectorAll('.historyItem').length"), 1);
  await click("기록 창 닫기"); await click("GitHub에 보관");
  await evaluate("document.querySelector('#token').value='test-not-a-real-token'");
  assert.equal(await evaluate(`localStorage.getItem(${storageKey}).includes('test-not-a-real-token')`), false);
  await click("연결 정보 지우기"); await click("GitHub 창 닫기");
  await close(); await open();
  await waitFor("document.querySelector('#version').textContent.length > 0");
  assert.equal(await evaluate("document.querySelector('#draft').value"), fixed);
  assert.equal(await evaluate("document.querySelector('#sourceInput').value"), initial.text);
  assert.equal(await evaluate("document.querySelector('#sourceInput').readOnly"), true);
  const inputs = ["결과가 저장되어집니다.", "예산은 380,000원입니다. 명세는 https://example.com/docs 에 있습니다.", "## 제목\n\n초안 작성 후 문장 구조 검토 과정을 거칩니다."];
  const { lintText } = await import("../../npm/src/index.js");
  const browserFindings = await evaluate(`import('./npm/src/index.js').then(engine=>${JSON.stringify(inputs)}.map(text=>engine.lintText(text)))`);
  assert.deepEqual(browserFindings, inputs.map((text) => lintText(text)));
  await click("새 글"); await click("기록하고 열기");
  await waitFor("document.querySelector('#sourceInput').value === ''");
  assert.equal(await evaluate("document.querySelector('#draft').disabled"), true);
  const composing = "원고가 저장되어집니다.";
  await evaluate(`document.querySelector('#sourceInput').dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));document.querySelector('#sourceInput').value=${JSON.stringify(composing)};document.querySelector('#sourceInput').dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true}));`);
  assert.equal(await evaluate("document.querySelector('#fixAllButton').disabled"), true);
  await evaluate("document.querySelector('#sourceInput').dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}))");
  await waitFor("!document.querySelector('#fixAllButton').disabled");
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem(${storageKey})).draft.original`), composing);
  await click("원문으로 시작");
  assert.equal(await evaluate("document.querySelector('#draft').value"), composing);
  await enter("draft", "<img src=x onerror=alert(1)> 원고가 저장됩니다.", "insertFromPaste");
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem(${storageKey})).draft.original`), composing);
  assert.equal(await evaluate("document.querySelectorAll('#highlights img, #findings img').length"), 0);
  await enter("draft", "");
  assert.equal(await evaluate("document.querySelector('#saveButton').disabled"), true);
  assert.equal(await evaluate("document.querySelector('#sourceInput').value"), composing);
  const result = { initial, fixed, browserParity: true, restored: true, inputEscaped: true, sourcePreserved: true, composition: true };
  await writeFile(resolve(output, "result.json"), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ viewport: initial.width, initialFindings: initial.count, browserParity: true, restored: true, sourcePreserved: true, composition: true }));
} finally {
  if (attached) await client.detachSession(attached.output);
  if (opened) await client.closeTarget(opened.output.targetRef);
  const resources = (await client.inspectSpace()).output.resources;
  assert.equal(resources.targets, 0); assert.equal(resources.sessions, 0); assert.equal(resources.artifacts, 0);
  await client.close();
}
