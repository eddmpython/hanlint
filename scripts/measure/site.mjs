/** 설치된 pyproc 공개 제어로 편집, 원문 보호, 기록 복원과 화면을 실측한다. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const require = createRequire(new URL("../../npm/package.json", import.meta.url));
const { PyProcControlClient } = await import(pathToFileURL(require.resolve("pyproc/control")));
const [config, output, url = "http://127.0.0.1:4179"] = process.argv.slice(2);
if (!config || !output) throw new Error("node scripts/measure/site.mjs <manifest> <공통 실행 공간 출력> [URL]");
await mkdir(output, { recursive: true });
const client = await PyProcControlClient.start(config);
let opened, attached;
try {
  opened = await client.openTarget(url, { expectedRisk: "externalEffect", waitUntil: "load" });
  attached = await client.attachSession(opened.output.targetRef);
  async function evaluate(expression) {
    const result = await client.command(attached.output, "Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }, { expectedRisk: "externalEffect" });
    if (result.output.result.exceptionDetails) throw new Error(JSON.stringify(result.output.result.exceptionDetails));
    return result.output.result.result.value;
  }
  async function waitFor(expression) {
    const matched = await evaluate(`new Promise(resolve => { const until = Date.now() + 20000; const timer = setInterval(() => { if (${expression}) {clearInterval(timer);resolve(true)} else if(Date.now() > until) {clearInterval(timer);resolve(false)} }, 80); })`);
    if (!matched) console.error(await evaluate("({text:document.querySelector('#draft').value,summary:document.querySelector('#reviewSummary').textContent,notice:document.querySelector('#notice').textContent,storage:document.querySelector('#storageStatus').textContent,original:document.querySelector('#originalText').textContent})"));
    assert.equal(matched, true, expression);
  }
  async function click(name, role = "button") {
    await evaluate(`Array.from(document.querySelectorAll('button,[role=tab]')).find(node=>node.textContent.trim()===${JSON.stringify(name)} || node.getAttribute('aria-label')===${JSON.stringify(name)})?.scrollIntoView({block:'center'})`);
    const eyes = client.perception(attached.output);
    const situation = await eyes.situate({ objective: `한린트 ${name}`, requirements: [{ requirementRef: "requirement:button", select: { role, name, actionable: true }, need: ["fact", "affordance"], cardinality: "one" }] });
    await eyes.actAffordance(situation.requirement("requirement:button").oneAffordance("click"), { intent: `한린트 ${name}` });
  }
  async function capture(name) {
    const captured = await client.act(attached.output, [{ kind: "screenshot", format: "png", expectedRisk: "read" }]);
    await writeFile(resolve(output, `${name}.png`), captured.attachments[0].bytes);
    await client.deleteArtifact(captured.output.actions[0].result.artifactRef);
  }
  await evaluate("localStorage.removeItem('hanlint.workspace.v1:/')");
  await client.detachSession(attached.output); attached = null;
  await client.closeTarget(opened.output.targetRef); opened = null;
  opened = await client.openTarget(url, { expectedRisk: "externalEffect", waitUntil: "load" });
  attached = await client.attachSession(opened.output.targetRef);
  await waitFor("document.querySelectorAll('.findingCard').length > 0");
  const initial = await evaluate("({width:innerWidth,overflow:document.documentElement.scrollWidth > innerWidth,channels:[...document.querySelectorAll('#channels a')].map(a=>a.href),text:document.querySelector('#draft').value,version:document.querySelector('#version').textContent,count:document.querySelectorAll('.findingCard').length,firstCard:document.querySelector('.findingCard').getBoundingClientRect().top})");
  assert.equal(initial.overflow, false);
  assert.equal(initial.channels.length, 5);
  await capture("firstView");
  await click("바로 고치기");
  await waitFor("!document.querySelector('#draft').value.includes('저장되어집니다') && document.querySelectorAll('.findingCard').length > 0");
  const fixed = await evaluate("document.querySelector('#draft').value");
  assert.notEqual(fixed, initial.text);
  await click("되돌리기");
  await waitFor(`document.querySelector('#draft').value === ${JSON.stringify(initial.text)} && !document.querySelector('#fixAllButton').disabled`);
  await click("바로 고치기");
  await waitFor("!document.querySelector('#draft').value.includes('저장되어집니다') && document.querySelectorAll('.findingCard').length > 0");
  await click("전후 비교");
  assert.equal(await evaluate("document.querySelector('#originalPane').hidden"), false);
  await click("수정본 기록");
  await click("이 수정본 남기기");
  await waitFor("JSON.parse(localStorage.getItem('hanlint.workspace.v1:/')).records.length === 1");
  await click("고침 기억", "tab");
  await waitFor("document.querySelectorAll('#memory .memoryItem').length > 0");
  await capture("remember");
  await click("doublePassive 3줄 고침 기억");
  await click("내 고침으로 기억");
  await waitFor("JSON.parse(localStorage.getItem('hanlint.workspace.v1:/')).patches.length === 1");
  await evaluate(`document.querySelector('#draft').value=${JSON.stringify(initial.text)}; document.querySelector('#draft').dispatchEvent(new InputEvent('input',{bubbles:true}))`);
  await click("지적", "tab");
  await waitFor("Array.from(document.querySelectorAll('#findings button')).some(node=>node.textContent==='기억한 고침 적용')");
  await click("기억한 고침 적용");
  await waitFor("!document.querySelector('#draft').value.includes('저장되어집니다') && document.querySelectorAll('.findingCard').length > 0");
  await evaluate(`document.querySelector('#draft').value=${JSON.stringify(fixed)}; document.querySelector('#draft').dispatchEvent(new InputEvent('input',{bubbles:true}))`);
  await waitFor("document.querySelectorAll('.findingCard').length > 0");
  await click("원문 보호", "tab");
  assert.ok((await evaluate("document.querySelector('#protection').innerText")).includes("변화 없음"));
  await click("내 기록");
  assert.equal(await evaluate("document.querySelectorAll('.historyItem').length"), 1);
  await click("기록 창 닫기");
  await click("GitHub에 보관");
  await evaluate("document.querySelector('#token').value='test-not-a-real-token'");
  assert.equal(await evaluate("localStorage.getItem('hanlint.workspace.v1:/').includes('test-not-a-real-token')"), false);
  await click("연결 정보 지우기");
  assert.equal(await evaluate("document.querySelector('#token').value"), "");
  await click("GitHub 창 닫기");
  await client.detachSession(attached.output); attached = null;
  await client.closeTarget(opened.output.targetRef); opened = null;
  opened = await client.openTarget(url, { expectedRisk: "externalEffect", waitUntil: "load" });
  attached = await client.attachSession(opened.output.targetRef);
  await waitFor("document.querySelector('#version').textContent.length > 0");
  assert.equal(await evaluate("document.querySelector('#draft').value"), fixed);
  assert.equal(await evaluate("JSON.parse(localStorage.getItem('hanlint.workspace.v1:/')).records.length"), 1);
  const inputs = ["결과가 저장되어집니다.", "예산은 380,000원입니다. 명세는 https://example.com/docs 에 있습니다.", "## 제목\n\n가상환경 생성 후 패키지 설치 확인 절차를 따릅니다."];
  const { lintText } = await import("../../npm/src/index.js");
  const browserFindings = await evaluate(`import('./npm/src/index.js').then(engine=>${JSON.stringify(inputs)}.map(text=>engine.lintText(text)))`);
  assert.deepEqual(browserFindings, inputs.map((text) => lintText(text)));
  await evaluate("document.querySelector('#draft').select(); const paste = new DataTransfer(); paste.setData('text/plain', '원고가 저장되어집니다.'); document.querySelector('#draft').dispatchEvent(new ClipboardEvent('paste',{bubbles:true,cancelable:true,clipboardData:paste}))");
  await waitFor("JSON.parse(localStorage.getItem('hanlint.workspace.v1:/')).draft.original === '원고가 저장되어집니다.' && !document.querySelector('#fixAllButton').disabled");
  await click("바로 고치기");
  await waitFor("document.querySelector('#draft').value === '원고가 저장됩니다.'");
  assert.equal(await evaluate("JSON.parse(localStorage.getItem('hanlint.workspace.v1:/')).draft.original"), "원고가 저장되어집니다.");
  await evaluate("document.querySelector('#draft').value='<img src=x onerror=alert(1)> 결과가 저장되어집니다.'; document.querySelector('#draft').dispatchEvent(new InputEvent('input',{bubbles:true}))");
  await waitFor("document.querySelector('#highlights').textContent.includes('<img') && document.querySelector('#reviewSummary').textContent !== '수정한 문장을 다시 읽고 있어요.'");
  assert.equal(await evaluate("document.querySelectorAll('#highlights img, #findings img').length"), 0);
  await writeFile(resolve(output, "result.json"), JSON.stringify({ initial, fixed, browserParity: true, restored: true, inputEscaped: true }, null, 2));
  console.log(JSON.stringify({ viewport: initial.width, initialFindings: initial.count, firstCard: initial.firstCard, browserParity: true, restored: true, inputEscaped: true }));
} finally {
  if (attached) await client.detachSession(attached.output);
  if (opened) await client.closeTarget(opened.output.targetRef);
  const resources = (await client.inspectSpace()).output.resources;
  assert.equal(resources.targets, 0); assert.equal(resources.sessions, 0); assert.equal(resources.artifacts, 0);
  await client.close();
}
