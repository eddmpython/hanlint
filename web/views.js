// @ts-check
/** 검사 결과, 원문 보호와 승인 기억의 화면 표현. */
import { element, button, get } from "./dom.js";

function empty(parent, title, description) {
  const node = element("div", "emptyState");
  node.append(element("strong", "", title), document.createTextNode(description));
  parent.append(node);
}

function findingDetail(result, index, handlers) {
  const finding = result.report.findings[index], detail = element("div", "findingDetail");
  detail.append(element("p", "findingWhy", finding.why));
  if (finding.exemplar) {
    const example = element("div", "example");
    example.append(element("div", "exampleLabel", "이렇게 고친 본보기"), element("div", "exampleAfter", finding.exemplar.after));
    detail.append(example);
  }
  const actions = element("div", "findingActions");
  actions.append(button("이 지적은 맞지 않아요", () => handlers.reject(finding)));
  if (finding.patch) actions.append(button("기억한 고침 적용", () => handlers.patch(index), "secondary small"));
  else if (result.findings[index].replacement !== null) actions.append(button("이대로 고치기", () => handlers.fix(index), "secondary small"));
  else actions.append(button("문장으로 이동 ↗", () => handlers.locate(finding)));
  detail.append(actions);
  return detail;
}

export function renderFindings(result, handlers) {
  const root = get("findings");
  root.replaceChildren();
  const findings = result.report.findings, groups = new Map();
  get("findingCount").textContent = String(findings.length);
  const errors = findings.filter((item) => item.severity === "error").length;
  get("reviewSummary").textContent = findings.length ? `고칠 곳 ${errors} · 살펴볼 곳 ${findings.length - errors}` : "현재 기준에서 발견한 지적이 없어요.";
  get("fixAllButton").disabled = !result.findings.some((item) => item.replacement !== null);
  if (!findings.length) empty(root, result.document.sentences.length ? "이제 한 번 읽어 보세요." : "어떤 글을 쓰고 있나요?", result.document.sentences.length ? "뜻과 말투까지 마음에 드는지는 직접 확인해 주세요." : "왼쪽에 글을 넣으면 고칠 곳을 함께 살펴볼게요.");
  findings.forEach((finding, index) => {
    const key = JSON.stringify([finding.line, finding.quote]);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(index);
  });
  let number = 0;
  for (const [key, indices] of groups) {
    const finding = findings[indices[0]], notice = indices.every((index) => findings[index].severity === "notice");
    const card = element("article", `findingCard${notice ? " noticeCard" : ""}`);
    card.dataset.finding = key;
    const summary = element("div", "findingHeading");
    summary.append(element("span", "findingNumber", String(++number).padStart(2, "0")),
      element("h3", "findingQuote", finding.quote));
    card.append(summary, ...indices.map((index) => findingDetail(result, index, handlers)));
    root.append(card);
  }
}

export function renderProtection(result) {
  const root = get("protection");
  root.replaceChildren();
  const surface = result.protection.changes;
  const pairs = [["숫자", "Numbers", "numbers"], ["URL", "Urls", "urls"], ["인라인 코드", "Code", "code"], ["링크 목적지", "Links", "links"]];
  for (const [label, suffix, field] of pairs) {
    const count = (surface[`missing${suffix}`]?.length ?? 0) + (surface[`unexpected${suffix}`]?.length ?? 0);
    const row = element("div", "protectionRow");
    row.append(element("strong", "", label), element("span", "", count ? `${count}개 변화` : `원문 ${result.protection.surface[field].length}개 · 변화 없음`));
    root.append(row);
    if (surface[`missing${suffix}`]?.length) root.append(element("p", "protectionWarning", `빠진 ${label}: ${surface[`missing${suffix}`].join(", ")}`));
    if (surface[`unexpected${suffix}`]?.length) root.append(element("p", "protectionWarning", `추가한 ${label}: ${surface[`unexpected${suffix}`].join(", ")}`));
  }
  const row = element("div", "protectionRow"), changes = result.protection.outline.mismatches;
  row.append(element("strong", "", "제목 순서 (H2)"), element("span", "", changes.length ? `${changes.length}개 변화` : "원문과 같은 순서"));
  root.append(row);
  if (changes.length) root.append(element("p", "protectionWarning", JSON.stringify(changes)));
  const shape = element("div", "shapeRow"), doc = result.document;
  shape.append(element("span", "", `문장 ${doc.sentences.length}개`), element("span", "", `문단 ${doc.paragraphs.length}개`), element("span", "", `절 ${doc.sections.length}개`));
  root.append(shape);
}

export function renderMemory(result, patches, canApprove, handlers) {
  const root = get("memory");
  get("memoryPanel").hidden = !result.learned.exemplars.length && !patches.length;
  root.replaceChildren();
  for (const candidate of result.learned.exemplars) {
    const item = element("article", "memoryItem");
    item.append(element("h3", "", `${candidate.beforeLine}줄에서 고친 문장`), element("p", "", `전: ${candidate.before}`), element("p", "", `후: ${candidate.after}`));
    const remembered = patches.some((patch) => patch.rule === candidate.rule && patch.before === candidate.before && patch.after === candidate.after && patch.presets.includes(candidate.presets[0]));
    if (remembered) item.append(element("span", "approved", "내 고침으로 기억했어요"));
    else {
      const approve = button(canApprove ? "뜻 유지 확인 · 고침 기억" : "먼저 수정본을 기록해 주세요", () => handlers.approve(candidate), "secondary small");
      approve.setAttribute("aria-label", `${candidate.rule} ${candidate.beforeLine}줄 고침 기억`);
      approve.disabled = !canApprove;
      item.append(approve);
    }
    root.append(item);
  }
  if (!result.learned.exemplars.length) empty(root, "실제 고침에서 시작해요", "문장을 고쳐 지적이 사라지면 기억할 후보가 나타납니다. 모든 재작성에서 후보를 추측하지는 않습니다.");
  if (patches.length) {
    root.append(element("h3", "exampleLabel", `기억 중인 고침 ${patches.length}개`));
    patches.forEach((patch, index) => {
      const item = element("article", "memoryItem");
      item.append(element("p", "", `${patch.before} → ${patch.after}`), button("이 고침 잊기", () => handlers.forget(index)));
      root.append(item);
    });
  }
}
