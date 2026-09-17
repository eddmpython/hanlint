// @ts-check
/** 소스의 글 마디와 글 시트. 파이썬 tests/document/testSourceText.py, tests/report/testSheet.py 와 같은 사례다. */
import assert from "node:assert/strict";
import test from "node:test";

import { parseSheet, renderSheet, renderSheetJson, replaceLiteral, sourceLiterals } from "../src/index.js";
import { finding } from "../src/rules/finding.js";

const JSX = [
  "// 주석의 한국어는 글이 아니다",
  "const LABELS = { pending: '승인 대기', failed: \"요청 실패\" }",
  "console.log('개발자만 보는 줄')",
  "throw new Error('내부 오류')",
  "<p>접수 실패 · 코드: {failure}</p>",
  "<span>{count}개 회사</span>",
  "<div>{list.map((x) => <Row label='한글' />)}</div>",
  "<b onClick={() => go('가')}>확인</b>",
  "const t = `최대 ${count}개 · 추가 불가`",
  "/* 블록 주석의 한국어 */ const u = 'ok'",
  "",
].join("\n");

test("quoted text and JSX text with expressions", () => {
  assert.deepEqual(
    sourceLiterals(JSX, "a.jsx").map((item) => [item.line, item.text]),
    [
      [2, "승인 대기"],
      [2, "요청 실패"],
      [5, "접수 실패 · 코드: {failure}"],
      [6, "{count}개 회사"],
      [7, "한글"],
      [8, "가"],
      [8, "확인"],
      [9, "최대 ${count}개 · 추가 불가"],
    ],
  );
});

test("rust continuation joins and the test module tail is dropped", () => {
  const source = 'fn f() -> Option<&str> { Some("설치 실패\\n\\n\\\n             node build") }\n#[cfg(test)]\nmod tests { fn t() { let s = "시험 문자열"; } }\n';
  assert.deepEqual(
    sourceLiterals(source, "a.rs").map((item) => [item.line, item.text]),
    [[1, "설치 실패\\n\\nnode build"]],
  );
});

test("arrow and template artifacts are not text", () => {
  const first = "const rows = list.map((step) => ({ scopeAddress: step.asset, visibleNameKo: `${step.label} 복구 단계 실행` }))\n";
  assert.deepEqual(sourceLiterals(first, "a.js").map((item) => [item.line, item.text]), [[1, "${step.label} 복구 단계 실행"]]);
  const second = "const a = `x`; const b = { label: `${n}개`, note: '한글' }; f(<i aria-label={ok ? '가' : '나'}>확인</i>)\n";
  assert.deepEqual(
    sourceLiterals(second, "a.jsx").map((item) => [item.line, item.text]),
    [[1, "${n}개"], [1, "한글"], [1, "가"], [1, "나"], [1, "확인"]],
  );
  const third = "<section role=\"status\" aria-label={busy ? '자료 갱신 중' : '자료 불러오는 중'} aria-live=\"polite\">\n";
  assert.deepEqual(sourceLiterals(third, "a.jsx").map((item) => [item.line, item.text]), [[1, "자료 갱신 중"], [1, "자료 불러오는 중"]]);
  assert.deepEqual(sourceLiterals("const s = 'it\\'s 한글'\n", "a.js").map((item) => item.text), ["it\\'s 한글"]);
  const fourth = "<button disabled={page >= pageCount} onClick={() => go(page + 1)}>다음</button> {a > b ? '큼' : '작음'}\n";
  assert.deepEqual(sourceLiterals(fourth, "a.jsx").map((item) => item.text), ["다음", "큼", "작음"]);
});

test("replaceLiteral only when unique", () => {
  assert.deepEqual(replaceLiteral("a = '요청 실패'", "요청 실패", "요청 없음"), ["a = '요청 없음'", 1]);
  assert.deepEqual(replaceLiteral("a = '요청'; b = '요청'", "요청", "x"), ["a = '요청'; b = '요청'", 2]);
  assert.deepEqual(replaceLiteral("a = 'x'", "없음", "y"), ["a = 'x'", 0]);
});

const ROWS = [
  { file: "src/a.jsx", line: 4, text: "요청을 완료하지 못했습니다", findings: [finding("screenSentence", 1, "글", "실패를 문장으로 쓴 것이다")], fix: "" },
  { file: "src/a.jsx", line: 9, text: "값 | 단위", findings: [], fix: "" },
];

test("sheet renders and parses back", () => {
  const sheet = renderSheet(ROWS, "screen", 1);
  assert.ok(sheet.includes("| 1 | src/a.jsx:4 | 요청을 완료하지 못했습니다 | screenSentence: 실패를 문장으로 쓴 것이다 |  |"));
  assert.ok(sheet.includes("| 2 | src/a.jsx:9 | 값 \\| 단위 |  |  |"));
  const edited = sheet
    .replace("실패를 문장으로 쓴 것이다 |  |", "실패를 문장으로 쓴 것이다 | 요청 실패 |")
    .replace("| 값 \\| 단위 |  |  |", "| 값 \\| 단위 |  | 값 \\| 단위 x |");
  const parsed = parseSheet(edited);
  assert.deepEqual(parsed.problems, []);
  assert.deepEqual(
    parsed.rows.map((row) => [row.file, row.line, row.text, row.fix]),
    [
      ["src/a.jsx", 4, "요청을 완료하지 못했습니다", "요청 실패"],
      ["src/a.jsx", 9, "값 | 단위", "값 | 단위 x"],
    ],
  );
  const data = JSON.parse(renderSheetJson(ROWS, "screen", 1));
  assert.equal(data.rows[0].findings[0].rule, "screenSentence");
});

test("bad rows are reported", () => {
  const parsed = parseSheet("| 1 | 자리없음 | 글 | 지적 | 고침 |\n| 2 | a:1 | 글 |\n");
  assert.deepEqual(parsed.rows, []);
  assert.deepEqual(parsed.problems, ["1행: 자리 `자리없음` 가 경로:줄 이나 경로:줄:칸 꼴이 아니다", "2행: 칸이 3개다. 5개여야 한다"]);
});
