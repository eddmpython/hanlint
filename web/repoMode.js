// @ts-check
/**
 * 저장소 모드. GitHub 주소 하나로 소스의 화면 글을 표로 보고, 고침 칸을 적어 시트로 내려받는다.
 * 코어는 CLI `hanlint sheet` 와 같은 sheetRows 이고 (워커의 `sheet` 액션), 내려받은 시트는 `hanlint sheet apply` 가 그대로 읽는다.
 * 저장소의 글은 문자열로만 다루고 textContent 로만 그린다.
 */
import { get, element, button, download } from "./dom.js";
import { RepoSource, blobUrl, checkBudget, parseRepoUrl, selectFiles } from "./repoSource.js";
import { RepoWriter } from "./repoWrite.js";

/** 마지막에 연 주소 하나만 기억한다. 기록 JSON (records.js) 과는 다른 키다. */
const REPO_KEY = "hanlint.repo";
/** 워커 요청 하나에 넣는 파일 수와 바이트. EngineClient 의 30초 안에 넉넉히 끝나는 크기다. */
const BATCH_FILES = 20;
const BATCH_BYTES = 400_000;
/** 묶음 하나의 검사 제한. 편집기의 기본 30초보다 길게 주어 큰 묶음이 워커를 다시 띄우지 않게 한다. */
const SHEET_TIMEOUT_MS = 60_000;
const TOGGLED = ["sampleButton", "newButton", "repoButton"];
const TEXT_FILE = /\.(md|markdown|txt)$/i;
const COLUMNS = ["자리", "글", "지적", "고침"];
const CUE = /^`[^`]+`/;

function fileName(path) {
  return path.slice(path.lastIndexOf("/") + 1);
}

function folderName(path) {
  const cut = path.lastIndexOf("/");
  return cut < 0 ? "" : path.slice(0, cut);
}

function placeKey(row) {
  return `${row.file}:${row.line}:${row.column}`;
}

function sameFilter(a, b) {
  return Boolean(a) && Boolean(b) && a.rule === b.rule && Boolean(a.proposed) === Boolean(b.proposed);
}

/** 원고로 열 수 있는 글 파일 (md, txt) 을 가리키는 주소인가. 저장소 모드 대신 원문으로 연다. */
export function isTextFileUrl(parsed) {
  return parsed !== null && parsed.ref !== null && TEXT_FILE.test(parsed.path);
}

export class RepoMode {
  /**
   * @param {{ engine: { request(payload: object, timeout?: number): Promise<any> }, notify(message: string, error?: boolean): void, onEnter(): void, onLeave(): void }} deps
   * @param {RepoSource} source
   */
  constructor(deps, source = new RepoSource()) {
    this.deps = deps;
    this.source = source;
    this.writer = new RepoWriter(deps.engine);
    this.active = false;
    /** 지금 도는 불러오기. 새 불러오기나 모드 나가기가 끊는다. */
    this.controller = null;
    this.sheetRun = 0;
    this.previousPreset = "blog";
    /** 사람이 적은 고침. 자리 키 → 글. 표를 다시 만들어도 남기고 새 저장소를 열면 비운다. */
    this.edited = new Map();
    /** 고른 칩. null 이면 전체다. 새 표를 만들면 유지하고 저장소를 바꾸면 비운다. */
    this.filter = null;
    this.reset();
    get("repoButton").onclick = () => this.enter();
    get("repoLeaveButton").onclick = () => this.leave();
    get("repoLoadButton").onclick = () => this.load(get("repoUrl").value);
    get("repoUrl").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); this.load(get("repoUrl").value); } });
    get("repoAll").addEventListener("change", () => this.runSheet());
    get("sheetDownloadButton").onclick = () => this.downloadSheet();
    get("repoWriteButton").onclick = () => this.openWrite();
    get("writeRun").onclick = () => this.writeBack();
    get("writeClear").onclick = () => { this.writer.forget(); get("writeToken").value = ""; get("writeStatus").textContent = "토큰을 지웠습니다."; };
  }

  reset() {
    this.filter = null;
    this.target = null;
    this.files = [];
    this.sources = [];
    this.rows = [];
    this.edited.clear();
  }

  /** 원문 대신 주소 칸과 파일 목록, 검사 결과 대신 표를 보인다. 주소를 주면 바로 불러온다. */
  enter(url = "") {
    if (!this.active) {
      this.active = true;
      this.deps.onEnter();
      this.previousPreset = get("preset").value;
      get("preset").value = "screen";
      this.toggle(true);
      this.summary("github.com 주소를 넣으면 소스의 화면 글을 표로 봅니다.");
      get("findings").replaceChildren();
      get("findingCount").textContent = "·";
      get("repoFiles").replaceChildren();
      get("sourceStats").textContent = "공개 저장소의 소스를 읽습니다";
      get("sheetDownloadButton").disabled = true;
      get("repoWriteButton").disabled = true;
      get("repoLoadButton").disabled = false;
    }
    let remembered = "";
    try { remembered = localStorage.getItem(REPO_KEY) ?? ""; } catch { remembered = ""; }
    get("repoUrl").value = url || get("repoUrl").value || remembered;
    if (url) this.load(url);
    else get("repoUrl").focus();
  }

  leave() {
    if (!this.active) return;
    this.active = false;
    this.controller?.abort();
    this.controller = null;
    this.sheetRun++;
    this.reset();
    this.toggle(false);
    get("preset").value = this.previousPreset;
    this.deps.onLeave();
  }

  /** 기억한 주소를 지운다. 브라우저 기록 삭제와 함께 부른다. */
  forget() {
    try { localStorage.removeItem(REPO_KEY); } catch { /* 기억은 편의일 뿐이다 */ }
  }

  toggle(on) {
    get("sourceInput").hidden = on;
    document.querySelector(".workGrid").classList.toggle("repoActive", on);
    get("repoPanel").hidden = !on;
    get("revisionSection").hidden = on;
    get("fixAllButton").hidden = on;
    get("sheetDownloadButton").hidden = !on;
    get("repoWriteButton").hidden = !on;
    get("repoLeaveButton").hidden = !on;
    for (const id of TOGGLED) get(id).hidden = on;
    get("fileLabel").hidden = on;
    get("sourceTitle").textContent = on ? "저장소" : "원문";
    get("resultTitle").textContent = on ? "화면 글 시트" : "검사 결과";
    get("resultOrigin").textContent = on ? "저장소" : "원문";
    get("resultHint").textContent = on ? "고침 칸을 적고 시트를 내려받아 hanlint sheet apply 로 되돌려 씁니다" : "확정할 수 있는 표현만 수정합니다";
  }

  summary(text) {
    get("reviewSummary").textContent = text;
  }

  /** 글 파일 (md, txt) 주소의 내용을 원고로 쓰기 위해 받는다. 저장소 모드에 들어가지 않는다. */
  async fetchText(parsed) {
    const controller = new AbortController();
    const target = { ...parsed, ref: parsed.ref };
    const [{ source }] = await this.source.fetchSources(target, [{ path: target.path }], undefined, controller.signal);
    return { text: source, title: fileName(target.path).replace(TEXT_FILE, "") };
  }

  /** 주소 → 브랜치 → 트리 → 고르기 → 예산 → raw → 표. 새 불러오기나 나가기가 오면 이전 것을 끊고 결과를 버린다. */
  async load(text) {
    const parsed = parseRepoUrl(text);
    if (!parsed) return this.deps.notify("github.com/계정/저장소 꼴의 주소를 넣어 주세요.", true);
    this.controller?.abort();
    const controller = new AbortController();
    this.controller = controller;
    const stale = () => controller !== this.controller || !this.active;
    get("repoLoadButton").disabled = true;
    get("sheetDownloadButton").disabled = true;
    get("findings").replaceChildren();
    get("findingCount").textContent = "·";
    get("repoFiles").replaceChildren();
    this.reset();
    try {
      this.summary("파일 목록 받는 중");
      const ref = parsed.ref ?? await this.source.defaultBranch(parsed.owner, parsed.repo, controller.signal);
      const [{ target, tree }, { suffixes }] = await Promise.all([
        this.source.resolveTree({ ...parsed, ref }, controller.signal),
        this.deps.engine.request({ action: "sourceSuffixes", preset: "screen", patches: [] }),
      ]);
      if (stale()) return;
      const { files, bytes, oversized } = selectFiles(tree, { suffixes, path: target.path });
      if (!files.length) throw new Error(`검사할 소스 파일 (${suffixes.join(", ")}) 이 없습니다.`);
      checkBudget(files, bytes);
      this.renderFiles(target, files, oversized);
      this.summary(`파일 내려받는 중 0 / ${files.length}`);
      const sources = await this.source.fetchSources(target, files, (done, total) => { if (!stale()) this.summary(`파일 내려받는 중 ${done} / ${total}`); }, controller.signal);
      if (stale()) return;
      this.target = target;
      this.files = files;
      this.sources = sources;
      this.controller = null;
      try { localStorage.setItem(REPO_KEY, text.trim()); } catch { /* 기억은 편의일 뿐이다 */ }
      await this.runSheet();
    } catch (error) {
      if (stale()) return;
      this.summary(error.message);
      this.deps.notify(error.message, true);
    } finally {
      if (controller === this.controller) this.controller = null;
      if (this.active && this.controller === null) get("repoLoadButton").disabled = false;
    }
  }

  renderFiles(target, files, oversized) {
    get("repoFiles").replaceChildren(...files.map((file) => element("li", "", file.path)));
    const skipped = oversized ? ` · 1MB 넘는 파일 ${oversized}개 제외` : "";
    get("sourceStats").textContent = `${target.owner}/${target.repo} @ ${target.ref} · 파일 ${files.length}개${skipped}`;
  }

  /** 받아 둔 소스로 표를 다시 만든다. 프리셋이나 `지적 없는 글도` 가 바뀔 때 다시 받지 않는다. 불러오는 중이면 그 끝에 만든다. */
  async runSheet() {
    if (!this.active || this.controller || !this.sources.length) return;
    const run = ++this.sheetRun;
    const target = this.target;
    const preset = get("preset").value;
    const everything = get("repoAll").checked;
    const batches = [];
    let batch = [];
    let bytes = 0;
    for (const item of this.sources) {
      if (batch.length && (batch.length >= BATCH_FILES || bytes + item.source.length > BATCH_BYTES)) { batches.push(batch); batch = []; bytes = 0; }
      batch.push(item);
      bytes += item.source.length;
    }
    if (batch.length) batches.push(batch);
    const rows = [];
    try {
      let done = 0;
      for (const files of batches) {
        this.summary(`검사 중 ${done} / ${this.sources.length}`);
        const part = await this.deps.engine.request({ action: "sheet", preset, patches: [], files, everything }, SHEET_TIMEOUT_MS);
        if (run !== this.sheetRun || target !== this.target) return;
        rows.push(...part);
        done += files.length;
      }
    } catch (error) {
      if (run !== this.sheetRun || target !== this.target) return;
      this.summary(error.message);
      return this.deps.notify(error.message, true);
    }
    for (const row of rows) if (this.edited.has(placeKey(row))) row.fix = this.edited.get(placeKey(row));
    this.rows = rows;
    this.render(everything);
  }

  render(everything) {
    const root = get("findings");
    root.replaceChildren();
    const flagged = this.rows.filter((row) => row.findings.length).length;
    get("findingCount").textContent = String(flagged);
    this.summary(`파일 ${this.files.length}개 · 글 ${this.rows.length}개 · 지적 있는 글 ${flagged}개`);
    get("sheetDownloadButton").disabled = false;
    this.refreshWrite();
    if (!this.rows.length) {
      const node = element("div", "emptyState");
      if (everything) node.append(element("strong", "", "이 파일들에서 한국어 화면 글을 찾지 못했어요."), document.createTextNode("다른 폴더나 브랜치의 주소를 넣어 보세요."));
      else node.append(element("strong", "", "이 기준에서 지적할 글이 없어요."), document.createTextNode("프리셋을 바꾸거나 지적 없는 글도 표에 넣어 볼 수 있어요."));
      root.append(node);
      return;
    }
    root.append(this.renderChips());
    const table = element("table", "sheetTable");
    const head = element("thead");
    const headRow = element("tr");
    for (const title of COLUMNS) headRow.append(element("th", "", title));
    head.append(headRow);
    const body = element("tbody");
    for (const row of this.rows) body.append(this.renderRow(row));
    table.append(head, body);
    root.append(table);
    this.applyFilter();
  }

  /** 규칙별 개수 칩. 누르면 그 규칙의 행만 보이고 다시 누르면 전체다. `제안 있음` 은 고침 칸이 채워진 행이다. */
  renderChips() {
    const counts = new Map();
    for (const row of this.rows) for (const rule of new Set(row.findings.map((finding) => finding.rule))) counts.set(rule, (counts.get(rule) ?? 0) + 1);
    const proposed = this.rows.filter((row) => row.fix).length;
    const chips = [["전체", this.rows.length, null], ...[...counts].sort((a, b) => b[1] - a[1]).map(([rule, count]) => [rule, count, { rule }])];
    if (proposed) chips.push(["제안 있음", proposed, { proposed: true }]);
    const group = element("div", "sheetChips");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "규칙별로 보기");
    for (const [label, count, filter] of chips) {
      const chip = button(`${label} ${count}`, () => { this.filter = sameFilter(this.filter, filter) ? null : filter; this.applyFilter(); }, "chip");
      chip.dataset.chip = filter ? (filter.rule ?? "proposed") : "all";
      group.append(chip);
    }
    return group;
  }

  /** 고른 칩에 맞는 행만 보인다. 행은 만들어 둔 채 숨기므로 적은 고침이 남는다. */
  applyFilter() {
    const rows = get("findings").querySelectorAll(".sheetTable tbody tr");
    rows.forEach((tr, index) => {
      const row = this.rows[index];
      const shown = !this.filter || (this.filter.proposed ? Boolean(row.fix) : row.findings.some((finding) => finding.rule === this.filter.rule));
      tr.hidden = !shown;
    });
    for (const chip of get("findings").querySelectorAll(".chip")) {
      const key = this.filter ? (this.filter.rule ?? "proposed") : "all";
      chip.setAttribute("aria-pressed", String(chip.dataset.chip === key));
    }
  }

  renderRow(row) {
    const tr = element("tr", row.findings.length ? "" : "quietRow");
    const place = element("td", "sheetPlace");
    const link = element("a", "", `${fileName(row.file)}:${row.line}`);
    link.href = blobUrl(this.target, row.file, row.line);
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.title = row.column > 0 ? `${row.file}:${row.line}:${row.column}` : `${row.file}:${row.line}`;
    place.append(link, element("small", "", folderName(row.file)));
    const text = element("td", "sheetText", row.text);
    const why = element("td", "sheetWhy");
    const byRule = new Map();
    for (const finding of row.findings) {
      if (!byRule.has(finding.rule)) byRule.set(finding.rule, []);
      if (!byRule.get(finding.rule).includes(finding.why)) byRule.get(finding.rule).push(finding.why);
    }
    // CLI 의 findingCell 과 같은 꼴: 첫 이유는 온전히, 같은 규칙의 나머지는 단서만.
    for (const [rule, reasons] of byRule) {
      const item = element("div", "sheetRule");
      item.append(element("strong", "", rule), element("span", "", reasons[0]));
      if (reasons.length > 1) {
        const cues = reasons.slice(1).map((reason) => CUE.exec(reason)?.[0]).filter((cue) => cue !== undefined);
        item.append(element("small", "", cues.length === reasons.length - 1 ? `또 ${cues.join(", ")}` : `또 ${reasons.length - 1}건`));
      }
      why.append(item);
    }
    const fix = element("td", "sheetFix");
    const input = element("input");
    input.value = row.fix;
    input.placeholder = "새 글";
    input.setAttribute("aria-label", `${row.text} 의 고침`);
    input.addEventListener("input", () => { row.fix = input.value; this.edited.set(placeKey(row), input.value); this.refreshWrite(); });
    fix.append(input);
    const cells = [place, text, why, fix];
    cells.forEach((cell, index) => { cell.dataset.label = COLUMNS[index]; });
    tr.append(...cells);
    return tr;
  }

  refreshWrite() {
    get("repoWriteButton").disabled = !this.target || !this.rows.some((row) => row.fix);
  }

  /** 쓰기 창. 고침이 적힌 행과 파일 수를 알려 주고 토큰을 받는다. */
  openWrite() {
    const fixed = this.rows.filter((row) => row.fix);
    const files = new Set(fixed.map((row) => row.file)).size;
    get("writeSummary").textContent = `${this.target.owner}/${this.target.repo} 의 ${this.target.ref} 브랜치에 고침 ${fixed.length}곳을 파일 ${files}개로 씁니다. 파일마다 commit 하나가 생깁니다.`;
    get("writeStatus").textContent = "";
    get("writeDialog").showModal();
    get("writeToken").focus();
  }

  /** 파일마다 읽고 바꾸고 commit 한다. 끝나면 바뀐 소스로 표를 다시 만든다. */
  async writeBack() {
    const status = get("writeStatus");
    const target = this.target;
    if (!target) return;
    get("writeRun").disabled = true;
    try {
      const result = await this.writer.write(target, this.rows, get("writeToken").value.trim(), (done, total, file) => { status.textContent = `쓰는 중 ${done} / ${total} · ${file}`; });
      for (const item of result.files) {
        if (item.source === null) continue;
        const entry = this.sources.find((source) => source.label === item.file);
        if (entry) entry.source = item.source;
        for (const row of this.rows) if (row.file === item.file && row.fix) this.edited.delete(placeKey(row));
      }
      const problems = result.files.flatMap((item) => item.failed);
      status.textContent = `적용 ${result.applied}곳, 실패 ${result.failed}곳` + (problems.length ? `\n${problems.join("\n")}` : "");
      if (result.applied) {
        this.deps.notify(`GitHub 에 ${result.applied}곳을 썼습니다. 표를 다시 만듭니다.`);
        await this.runSheet();
      }
    } catch (error) {
      status.textContent = error.message;
    } finally {
      get("writeRun").disabled = false;
    }
  }

  async downloadSheet() {
    if (!this.target) return;
    try {
      const markdown = await this.deps.engine.request({ action: "sheetText", preset: get("preset").value, patches: [], rows: this.rows, fileCount: this.files.length });
      download(`hanlint-sheet-${this.target.owner}-${this.target.repo}.md`, markdown, "text/markdown;charset=utf-8");
      this.deps.notify("시트를 받았습니다. 저장소 루트에서 hanlint sheet apply 시트.md 로 되돌려 씁니다.");
    } catch (error) {
      this.deps.notify(error.message, true);
    }
  }
}
