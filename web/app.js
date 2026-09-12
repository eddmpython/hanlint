// @ts-check
/** 편집, 원문 비교, 개인 기록과 선택한 GitHub 저장의 조립. */
import { channels } from "./channels.js";
import { get, element, button, download, highlight } from "./dom.js";
import { renderFindings, renderProtection, renderMemory } from "./views.js";
import { GitHubStore } from "./github.js";
import { EngineClient } from "./engineClient.js";
import { registerEditorTools } from "./modelTools.js";
import { newDraft, emptyWorkspace, parseWorkspace, serializeWorkspace, addRecord, contribution, storageKeyFor, MAX_TEXT, MAX_ARCHIVE_BYTES } from "./records.js";

const SAMPLE = "# 팀 문서를 조금 더 읽기 쉽게\n\n가상환경 생성 후 패키지 설치 확인 절차를 따릅니다. 결과가 저장되어집니다.\n\n## 파일을 저장하는 방법\n\n이 기능을 통해 파일 생성이 가능합니다. 저장 버튼을 누르면 report.csv가 만들어집니다.\n\n## 다음 사람이 읽을 때\n\n예산은 380,000원입니다. 자세한 명세는 https://example.com/docs 에 있습니다. 어려운 말을 줄이는 것만큼, 필요한 정보를 지키는 일도 중요합니다.";
const github = new GitHubStore();
const storageKey = storageKeyFor(location.pathname);
const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
const engine = new EngineClient(worker, (error) => {
  get("reviewSummary").textContent = error.message;
  notify(error.message, true);
});
let editVersion = 0, analysis = null, timer, noticeTimer, undo = [], storageEnabled = true;
let workspace = emptyWorkspace(newDraft(SAMPLE, "처음 만나는 한린트"));

function notify(message, error = false) {
  const node = get("notice");
  clearTimeout(noticeTimer);
  node.textContent = message;
  node.className = `notice${error ? " errorNotice" : ""}`;
  node.hidden = false;
  noticeTimer = setTimeout(() => { node.hidden = true; }, error ? 12000 : 6500);
}

function request(action, extra = {}, draft = workspace.draft, patches = workspace.patches) {
  return engine.request({ action, text: draft.text, original: draft.original, preset: draft.preset, patches, ...extra });
}

function persist() {
  if (!storageEnabled) return;
  try {
    localStorage.setItem(storageKey, serializeWorkspace(workspace));
    get("storageStatus").textContent = "이 브라우저에 임시 보관됨";
  } catch (error) {
    get("storageStatus").textContent = "저장하지 못함 · 기록을 내보내 주세요";
    notify(error.message || "브라우저 저장 공간이 부족합니다. 기록을 내보내 주세요.", true);
  }
}

function renderDraft() {
  const draft = workspace.draft;
  get("draft").value = draft.text;
  get("title").value = draft.title;
  get("preset").value = draft.preset;
  get("originalText").textContent = draft.original || "처음 수정본을 기록하면 원문 비교가 시작됩니다.";
  get("textStats").textContent = `${[...draft.text].length.toLocaleString()}자`;
  get("undoButton").disabled = !undo.length;
}

function isRecorded() {
  return workspace.records.some((record) => record.id === workspace.draft.id && record.text === workspace.draft.text && record.original === workspace.draft.original && record.preset === workspace.draft.preset);
}

function renderResult() {
  if (!analysis) return;
  renderFindings(analysis, { locate, reject: rejectFinding, fix: (index) => fix(index), patch: (index) => fix(index, "patch") });
  renderProtection(analysis);
  renderMemory(analysis, workspace.patches, isRecorded(), { approve, forget });
  highlight(workspace.draft.text, analysis.report.findings);
  get("version").textContent = `v${analysis.version}`;
  get("textStats").textContent = `${[...workspace.draft.text].length.toLocaleString()}자 · ${analysis.document.sentences.length}문장`;
}

async function analyze() {
  const current = editVersion;
  get("fixAllButton").disabled = true;
  try {
    const result = await request("analyze");
    if (current !== editVersion) return;
    analysis = result;
    renderResult();
  } catch (error) {
    if (current !== editVersion) return;
    get("reviewSummary").textContent = error.message;
    notify(error.message, true);
  }
}

function changed() {
  editVersion++;
  workspace.draft.updatedAt = new Date().toISOString();
  analysis = null;
  clearTimeout(timer);
  get("fixAllButton").disabled = true;
  get("reviewSummary").textContent = "수정한 문장을 다시 읽고 있어요.";
  get("findings").replaceChildren();
  get("protection").replaceChildren(element("p", "emptyState", "수정한 원고의 보호 조건을 확인하고 있어요."));
  get("memory").replaceChildren(element("p", "emptyState", "수정 전후를 다시 비교하고 있어요."));
  highlight(workspace.draft.text, []);
  get("textStats").textContent = `${[...workspace.draft.text].length.toLocaleString()}자`;
  persist();
  timer = setTimeout(analyze, 220);
}

function replaceText(text, remember = true) {
  if (remember) undo.push(workspace.draft.text);
  workspace.draft.text = text;
  renderDraft();
  changed();
}

async function fix(index, action = "fix") {
  const current = editVersion;
  try {
    const result = await request(action, { index });
    if (current !== editVersion) return notify("검사하는 동안 원고가 바뀌었습니다. 새 결과에서 다시 고쳐 주세요.");
    if (result.text === workspace.draft.text) return notify("지금 바로 적용할 고침이 없습니다. 지적의 본보기를 확인해 주세요.");
    if (!workspace.draft.original) workspace.draft.original = workspace.draft.text;
    replaceText(result.text);
    notify(`${result.applied.length}곳을 고쳤습니다. 되돌리기로 원래 표현을 복원할 수 있어요.`);
  } catch (error) { notify(error.message, true); }
}

function locate(finding) {
  const area = get("draft"), text = workspace.draft.text;
  const lines = text.split("\n");
  const start = lines.slice(0, finding.line - 1).reduce((total, line) => total + line.length + 1, 0);
  const fragment = finding.fragment || finding.quote;
  const at = text.indexOf(fragment, start);
  area.focus();
  const end = at >= 0 ? at + fragment.length : start + (lines[finding.line - 1]?.length ?? 0);
  area.setSelectionRange(at >= 0 ? at : start, end);
  const lineHeight = parseFloat(getComputedStyle(area).lineHeight);
  area.scrollTop = Math.max(0, (finding.line - 2) * lineHeight);
  get("highlights").scrollTop = area.scrollTop;
}

function confirmAction(message, label = "계속") {
  return new Promise((resolve) => {
    const dialog = get("confirmDialog");
    get("confirmText").textContent = message;
    get("confirmAccept").textContent = label;
    const finish = (value) => {
      dialog.close();
      get("confirmAccept").onclick = null;
      get("confirmCancel").onclick = null;
      dialog.oncancel = null;
      resolve(value);
    };
    get("confirmAccept").onclick = () => finish(true);
    get("confirmCancel").onclick = () => finish(false);
    dialog.oncancel = (event) => { event.preventDefault(); finish(false); };
    dialog.showModal();
  });
}

async function rejectFinding(finding) {
  const version = analysis?.version, preset = workspace.draft.preset;
  if (!await confirmAction(`이 지적이 문맥에 맞지 않는다고 기록할까요?\n\n${finding.quote}\n\n기본 규칙은 바뀌지 않으며, 내 기록에 판단을 남깁니다.`, "맞지 않는 지적으로 기록")) return;
  workspace.feedback.push({ rule: finding.rule, quote: finding.quote, why: finding.why, preset,
    judgment: "falsePositive", engineVersion: version ?? "unknown", at: new Date().toISOString() });
  persist();
  notify("맞지 않는 지적으로 기록했습니다. 기록 내보내기에 함께 담깁니다.");
}

async function approve(candidate) {
  if (!isRecorded()) return;
  if (!await confirmAction(`고친 문장의 뜻이 유지되고, 같은 원문에서 다시 제안해도 되는지 확인해 주세요.\n\n전: ${candidate.before}\n후: ${candidate.after}\n\n이 승인은 내 고침에만 적용됩니다.`, "내 고침으로 기억")) return;
  const patch = { rule: candidate.rule, before: candidate.before, after: candidate.after, moved: candidate.moved,
    sourceText: candidate.before, sentence: candidate.sentence, cue: candidate.cue, reader: candidate.reader, presets: candidate.presets };
  const next = workspace.patches.filter((item) => !(item.rule === patch.rule && item.sourceText === patch.sourceText && item.cue === patch.cue && item.reader === patch.reader && item.presets.some((preset) => patch.presets.includes(preset))));
  next.push(patch);
  try {
    await request("analyze", {}, workspace.draft, next);
    workspace.patches = next;
    persist();
    await analyze();
    notify("내 고침으로 기억했습니다. 같은 원문과 문맥에서 다시 제안합니다.");
  } catch (error) { notify(error.message, true); }
}

async function forget(index) {
  if (!await confirmAction("이 고침의 재사용 승인을 지울까요? 원고와 수정 이력은 남습니다.", "승인 지우기")) return;
  workspace.patches.splice(index, 1);
  persist();
  await analyze();
}

function showHistory() {
  const root = get("historyList");
  root.replaceChildren();
  if (!workspace.records.length) root.append(element("p", "emptyState", "아직 기록한 수정본이 없습니다. 편집기에서 수정본 기록을 눌러 주세요."));
  for (const record of [...workspace.records].reverse()) {
    const item = element("article", "historyItem");
    item.append(element("h3", "", record.title || "이름 없는 원고"), element("span", "historyDate", `${record.updatedAt.replace("T", " ").slice(0, 16)} UTC · ${record.preset}`), element("p", "", record.reason || "수정 이유를 남기지 않았어요."));
    const actions = element("div");
    actions.append(button("이 수정본 열기", async () => {
      if (!await confirmAction("현재 편집을 수정 이력에 보관하고 선택한 수정본을 열까요?", "기록 열기")) return;
      try { addRecord(workspace, analysis?.version ?? "unknown"); } catch (error) { return notify(error.message, true); }
      workspace.draft = { id: record.id, title: record.title, text: record.text, original: record.original, preset: record.preset, updatedAt: record.updatedAt };
      undo = [];
      get("historyDialog").close();
      renderDraft();
      changed();
    }, "secondary small"));
    actions.append(button("기여할 사례 내보내기", async () => {
      if (!await confirmAction("이 수정본의 원문과 수정 후 전문, 수정 이유를 사례 파일로 내려받습니다. 공유하기 전에 개인정보와 비공개 내용을 확인해 주세요. 자동으로 제출하지 않습니다.", "사례 파일 받기")) return;
      download("hanlintContribution.json", JSON.stringify(contribution(record, "submittedForReview"), null, 2));
      notify("사례 파일을 받았습니다. 검토한 뒤 GitHub Issues의 개선 제안에 첨부할 수 있어요.");
    }));
    actions.append(button("삭제", async () => {
      if (!await confirmAction("이 브라우저에서 선택한 수정본 하나를 삭제할까요?", "삭제")) return;
      workspace.records = workspace.records.filter((item) => item.recordId !== record.recordId);
      persist(); showHistory();
    }));
    item.append(actions); root.append(item);
  }
  if (!get("historyDialog").open) get("historyDialog").showModal();
}

async function importWorkspace(next, sha = null) {
  await request("analyze", {}, next.draft, next.patches);
  if (!await confirmAction("현재 브라우저 기록을 가져온 기록으로 교체할까요? 보관할 현재 기록이 있으면 취소하고 기록 내보내기를 먼저 해 주세요.", "가져온 기록 열기")) return false;
  workspace = next; undo = []; storageEnabled = true;
  if (sha) github.accept(sha);
  renderDraft(); changed();
  for (const id of ["historyDialog", "githubDialog"]) get(id).close();
  notify("원고와 수정 기록을 가져왔습니다.");
  return true;
}

async function gitAction(action) {
  get("githubSave").disabled = get("githubLoad").disabled = true;
  const status = get("githubStatus");
  status.textContent = "GitHub에 연결하고 있어요.";
  try {
    github.connect(get("repository").value.trim(), get("token").value.trim());
    if (action === "load") {
      const result = await github.load();
      const imported = await importWorkspace(result.workspace, result.sha);
      status.textContent = imported ? "기록을 가져왔습니다." : "가져오기를 취소했습니다.";
    } else {
      const snapshot = parseWorkspace(serializeWorkspace(workspace));
      if (!await confirmAction(`${github.repository} 저장소에 현재 원고와 수정 이력을 저장합니다. 공개 저장소이면 이 내용도 공개됩니다. 계속할까요?`, "이 저장소에 저장")) { status.textContent = "저장을 취소했습니다."; return; }
      await github.save(snapshot);
      status.textContent = "GitHub에 보관했습니다. 이후 편집은 다시 저장할 때 반영됩니다.";
      notify("내 GitHub 저장소에 원고와 수정 이력을 보관했습니다.");
    }
  } catch (error) { status.textContent = error.message; }
  finally { get("githubSave").disabled = get("githubLoad").disabled = false; }
}

function selectTab(name) {
  for (const tab of document.querySelectorAll("[role=tab]")) {
    const selected = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    get(`${tab.dataset.tab}Panel`).hidden = !selected;
  }
}

async function startDraft(text, title) {
  if (workspace.draft.text && !await confirmAction("현재 원고를 기록하고 다른 글을 열까요?", "기록하고 열기")) return;
  try { if (workspace.draft.text) addRecord(workspace, analysis?.version ?? "unknown"); }
  catch (error) { return notify(error.message, true); }
  workspace.draft = newDraft(text, title, workspace.draft.preset);
  undo = []; renderDraft(); changed();
  get("draft").focus();
}

for (const channel of channels) {
  const link = element("a", `channelLink ${channel.modifier ?? ""}`);
  link.href = channel.href; link.target = "_blank"; link.rel = "noopener noreferrer";
  link.title = channel.title ?? channel.name; link.setAttribute("aria-label", channel.name);
  // 채널의 고정 SVG만 넣고 원고나 가져온 자료는 이 경로에 전달하지 않는다.
  link.innerHTML = channel.icon;
  get("channels").append(link);
}

try {
  const saved = localStorage.getItem(storageKey);
  if (saved) workspace = parseWorkspace(saved);
} catch (error) {
  storageEnabled = false;
  get("storageStatus").textContent = "기존 기록을 읽지 못해 덮어쓰지 않습니다";
  notify(`기존 기록을 읽지 못했습니다. 기존 저장은 보존하고 예문을 열었습니다. ${error.message}`, true);
}

get("draft").addEventListener("paste", (event) => {
  const area = get("draft");
  if (area.selectionStart !== 0 || area.selectionEnd !== area.value.length) return;
  const text = event.clipboardData?.getData("text/plain");
  if (!text) return;
  event.preventDefault();
  if (text.length > MAX_TEXT) return notify("원고는 60,000자 이하로 붙여 넣어 주세요.", true);
  try { if (workspace.draft.text) addRecord(workspace, analysis?.version ?? "unknown"); }
  catch (error) { return notify(error.message, true); }
  workspace.draft = newDraft(text, "붙여 넣은 원고", workspace.draft.preset);
  undo = []; renderDraft(); changed();
  notify("붙여 넣은 글을 원문으로 삼았습니다. 지금부터 고친 내용을 비교할 수 있어요.");
});
get("draft").addEventListener("input", (event) => {
  if (event.isComposing) return;
  undo.push(workspace.draft.text);
  workspace.draft.text = get("draft").value;
  get("undoButton").disabled = false;
  changed();
});
get("draft").addEventListener("compositionend", () => { if (workspace.draft.text !== get("draft").value) undo.push(workspace.draft.text); workspace.draft.text = get("draft").value; get("undoButton").disabled = !undo.length; changed(); });
get("draft").addEventListener("scroll", () => { get("highlights").scrollTop = get("draft").scrollTop; });
get("title").addEventListener("input", () => { workspace.draft.title = get("title").value; persist(); });
get("preset").addEventListener("change", () => { workspace.draft.preset = get("preset").value; changed(); });
get("fixAllButton").onclick = () => fix(null);
get("undoButton").onclick = () => { if (undo.length) replaceText(undo.pop(), false); };
get("compareButton").onclick = () => {
  const show = get("originalPane").hidden;
  get("originalPane").hidden = get("currentLabel").hidden = !show;
  get("editColumns").classList.toggle("comparing", show);
  get("compareButton").setAttribute("aria-pressed", String(show));
};
get("sampleButton").onclick = () => startDraft(SAMPLE, "처음 만나는 한린트");
get("newButton").onclick = () => startDraft("", "새 원고");
get("downloadButton").onclick = () => download(`${workspace.draft.title || "원고"}.md`, workspace.draft.text, "text/markdown;charset=utf-8");
get("fileInput").onchange = async (event) => {
  const file = event.target.files[0]; event.target.value = "";
  if (!file) return;
  if (file.size > MAX_TEXT * 4) return notify("원고는 60,000자 이하 파일을 사용해 주세요.", true);
  const text = await file.text();
  if (text.length > MAX_TEXT) return notify("원고는 60,000자 이하 파일을 사용해 주세요.", true);
  await startDraft(text, file.name.replace(/\.[^.]+$/, "").slice(0, 100));
};
get("saveButton").onclick = () => {
  if (!analysis) return notify("검사가 끝난 뒤 수정본을 기록해 주세요.");
  if (!workspace.draft.text.trim()) return notify("먼저 원고를 써 주세요.");
  get("recordDialog").showModal();
};
get("recordAccept").onclick = async () => {
  try {
    if (!workspace.draft.original) workspace.draft.original = workspace.draft.text;
    const saved = addRecord(workspace, analysis?.version ?? "unknown", get("revisionReason").value, get("revisionOrigin").value);
    get("recordDialog").close(); get("revisionReason").value = "";
    persist(); renderDraft(); await analyze();
    notify(saved ? "수정본을 기록했습니다. 고침 기억에서 재사용할 문장을 확인해 보세요." : "같은 수정본이 이미 기록되어 있어요.");
  } catch (error) { notify(error.message, true); }
};
get("historyButton").onclick = showHistory;
get("exportButton").onclick = () => { try { download("hanlintWorkspace.json", serializeWorkspace(workspace)); } catch (error) { notify(error.message, true); } };
get("importInput").onchange = async (event) => {
  const file = event.target.files[0]; event.target.value = "";
  if (!file) return;
  try {
    if (file.size > MAX_ARCHIVE_BYTES) throw new Error("900 KB 이하 기록 파일을 사용해 주세요.");
    await importWorkspace(parseWorkspace(await file.text()));
  } catch (error) { notify(error.message, true); }
};
get("clearButton").onclick = async () => {
  if (!await confirmAction("이 브라우저의 원고, 수정 이력과 승인 고침을 모두 삭제할까요? GitHub 기록은 남습니다. 필요한 기록은 먼저 내보내 주세요.", "브라우저 기록 삭제")) return;
  try { localStorage.removeItem(storageKey); } catch (error) { return notify(error.message, true); }
  workspace = emptyWorkspace(newDraft("", "새 원고")); storageEnabled = true; undo = [];
  get("historyDialog").close(); renderDraft(); changed();
};
get("githubButton").onclick = () => get("githubDialog").showModal();
get("githubSave").onclick = () => gitAction("save");
get("githubLoad").onclick = () => gitAction("load");
get("disconnectButton").onclick = () => { github.disconnect(); get("token").value = get("repository").value = ""; get("githubStatus").textContent = "연결 정보를 지웠습니다."; };
for (const close of document.querySelectorAll("[data-close]")) close.onclick = () => get(close.dataset.close).close();
for (const tab of document.querySelectorAll("[role=tab]")) {
  tab.onclick = () => selectTab(tab.dataset.tab);
  tab.onkeydown = (event) => {
    const tabs = [...document.querySelectorAll("[role=tab]")], index = tabs.indexOf(tab);
    const next = event.key === "ArrowRight" ? (index + 1) % tabs.length : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault(); selectTab(tabs[next].dataset.tab); tabs[next].focus();
  };
}
window.addEventListener("pagehide", () => { persist(); github.disconnect(); get("token").value = ""; });
window.addEventListener("storage", (event) => {
  if (event.key !== storageKey) return;
  storageEnabled = false;
  get("storageStatus").textContent = "다른 탭의 기록 변경 · 자동 보관 중지";
  notify("다른 탭에서 기록이 바뀌었습니다. 현재 원고와 기록을 내보낸 뒤 새로고침해 주세요. 다른 탭의 기록은 덮어쓰지 않습니다.", true);
});
renderDraft();
analyze();
const unregisterTools = registerEditorTools(document.modelContext, {
  async inspect() { const result = await request("analyze"); return { findings: result.report.findings, protection: result.protection }; },
  async replace(text) { replaceText(text); clearTimeout(timer); await analyze(); return { text: workspace.draft.text, findings: analysis?.report.findings ?? [], updated: analysis !== null }; },
}, (error) => console.warn("한린트 편집 도구를 등록하지 못했습니다.", error.message));
window.addEventListener("pagehide", unregisterTools, { once: true });
