// @ts-check
/** 검사 결과, 원문 보호와 승인 기억의 화면 표현. */
import { element, button, get } from "./dom.js";

function empty(parent, title, description) {
  const node = element("div", "emptyState");
  node.append(element("strong", "", title), document.createTextNode(description));
  parent.append(node);
}

export function renderFindings(result, handlers) {
  const root = get("findings");
  root.replaceChildren();
  const findings = result.report.findings;
  get("findingCount").textContent = String(findings.length);
  const errors = findings.filter((item) => item.severity === "error").length;
  get("reviewSummary").textContent = findings.length ? `집은 자리 ${errors}곳 · 참고할 자리 ${findings.length - errors}곳` : "현재 기준에서 집힌 자리가 없습니다.";
  get("fixAllButton").disabled = !result.findings.some((item) => item.replacement !== null);
  if (!findings.length) empty(root, "지금은 남길 메모가 없어요", "문맥과 사실, 원하는 말투가 잘 담겼는지 한 번 읽어 보세요.");
  findings.forEach((finding, index) => {
    const card = element("article", "findingCard"), top = element("div", "findingTop");
    top.append(element("span", `findingBadge${finding.severity === "notice" ? " noticeBadge" : ""}`, finding.severity === "notice" ? "참고" : "집은 자리"), element("span", "findingRule", `${finding.line}줄 · ${finding.rule}`));
    card.append(top, button(finding.quote, () => handlers.locate(finding), "findingQuote"), element("p", "findingWhy", finding.why));
    if (finding.exemplar) {
      const example = element("div", "example");
      example.append(element("div", "exampleLabel", "이렇게 고친 본보기"), element("div", "exampleBefore", finding.exemplar.before), element("div", "exampleAfter", finding.exemplar.after));
      card.append(example);
    }
    const actions = element("div", "findingActions");
    actions.append(button("이 지적은 맞지 않아요", () => handlers.reject(finding)));
    if (finding.patch) actions.append(button("기억한 고침 적용", () => handlers.patch(index), "secondary small"));
    else if (result.findings[index].replacement !== null) actions.append(button("이곳 고치기", () => handlers.fix(index), "secondary small"));
    else actions.append(button("문장으로 이동 ↗", () => handlers.locate(finding)));
    card.append(actions);
    root.append(card);
  });
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
  root.replaceChildren();
  for (const candidate of result.learned.exemplars) {
    const item = element("article", "memoryItem");
    item.append(element("h3", "", candidate.rule), element("p", "", `전: ${candidate.before}`), element("p", "", `후: ${candidate.after}`));
    const remembered = patches.some((patch) => patch.rule === candidate.rule && patch.before === candidate.before && patch.after === candidate.after && patch.presets.includes(candidate.presets[0]));
    if (remembered) item.append(element("span", "approved", "내 고침으로 기억했어요"));
    else {
      const approve = button(canApprove ? "뜻을 확인하고 기억" : "먼저 수정본을 기록해 주세요", () => handlers.approve(candidate), "secondary small");
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
