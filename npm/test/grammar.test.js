// @ts-check
import assert from "node:assert/strict";
import test from "node:test";

import {
  ADJECTIVE,
  CAUSATIVE,
  COPULA,
  HAEYO,
  HANDA,
  HAPNIDA,
  IMPERATIVE,
  PASSIVE,
  PROPOSITIVE,
  VERB,
  convertRegister,
  decomposeVoice,
  documentRegister,
  parsePredicate,
  registerOfWord,
  render,
} from "../src/analysis/grammar/index.js";

const politeForms = [
  ["확인합니다", "확인한다", "확인해요"],
  ["있습니다", "있다", "있어요"],
  ["봅니다", "본다", "봐요"],
  ["엽니다", "연다", "열어요"],
  ["만듭니다", "만든다", "만들어요"],
  ["어렵습니다", "어렵다", "어려워요"],
  ["돕습니다", "돕는다", "도와요"],
  ["듣습니다", "듣는다", "들어요"],
  ["낫습니다", "낫다", "나아요"],
  ["그렇습니다", "그렇다", "그래요"],
  ["다릅니다", "다르다", "달라요"],
  ["보입니다", "보인다", "보여요"],
  ["했습니다", "했다", "했어요"],
  ["하겠습니다", "하겠다", "하겠어요"],
];

test("corpus predicate forms render in three registers", () => {
  for (const [source, handa, haeyo] of politeForms) {
    const predicate = parsePredicate(source);
    assert.ok(predicate);
    assert.equal(render(predicate, HAPNIDA), source);
    assert.equal(render(predicate, HANDA), handa);
    assert.equal(render(predicate, HAEYO), haeyo);
  }
});

test("plain forms go both ways", () => {
  const rows = [
    ["확인한다", "확인합니다", "확인해요"],
    ["연다", "엽니다", "열어요"],
    ["만든다", "만듭니다", "만들어요"],
    ["어렵다", "어렵습니다", "어려워요"],
    ["보인다", "보입니다", "보여요"],
    ["했다", "했습니다", "했어요"],
  ];
  for (const [source, hapnida, haeyo] of rows) {
    const predicate = parsePredicate(source);
    assert.ok(predicate);
    assert.equal(render(predicate, HANDA), source);
    assert.equal(render(predicate, HAPNIDA), hapnida);
    assert.equal(render(predicate, HAEYO), haeyo);
  }
});

test("copula, negative auxiliary, and moods keep their distinctions", () => {
  const explicit = parsePredicate("예시이다");
  assert.ok(explicit);
  assert.equal(explicit.kind, COPULA);
  assert.equal(render(explicit, HANDA), "예시이다");
  assert.equal(render(explicit, HAEYO), "예시예요");

  const adjective = parsePredicate("않습니다", "크지");
  const verb = parsePredicate("않습니다", "먹지");
  assert.ok(adjective && verb);
  assert.equal(adjective.kind, ADJECTIVE);
  assert.equal(verb.kind, VERB);

  const imperative = parsePredicate("확인하십시오");
  const propositive = parsePredicate("찾읍시다");
  assert.ok(imperative && propositive);
  assert.equal(imperative.mood, IMPERATIVE);
  assert.equal(render(imperative, HANDA), "확인하라");
  assert.equal(propositive.mood, PROPOSITIVE);
  assert.equal(render(propositive, HAEYO), "찾아요");
  assert.equal(parsePredicate("글자"), null);
});

test("register detection and conversion match the document contract", () => {
  assert.equal(registerOfWord("확인합니다"), HAPNIDA);
  assert.equal(registerOfWord("확인한다"), HANDA);
  assert.equal(registerOfWord("확인해요"), HAEYO);
  assert.deepEqual(documentRegister(["확인한다", "끝난다", "봅니다"], 0.7), ["섞임", 2 / 3]);
  assert.deepEqual(documentRegister(["확인한다", "끝난다", "봅니다"], 0.6), [HANDA, 2 / 3]);

  const source = "# 확인합니다\n\n값을 확인합니다.\n\n| 확인합니다 |\n\n```text\n확인합니다.\n```\n";
  assert.deepEqual(convertRegister(source, HANDA), {
    text: "# 확인합니다\n\n값을 확인한다.\n\n| 확인합니다 |\n\n```text\n확인합니다.\n```\n",
    converted: 1,
    skipped: 0,
  });
});

test("voice decomposition has positive and negative pairs", () => {
  assert.deepEqual(decomposeVoice("쓰여지"), {
    surface: "쓰여지",
    kind: PASSIVE,
    base: "쓰이",
    markers: ["접미 피동", "어지"],
    reduced: "쓰이",
  });
  assert.deepEqual(decomposeVoice("쉽게 만들었다"), {
    surface: "쉽게 만들었다",
    kind: CAUSATIVE,
    base: "쉽",
    markers: ["게", "만들"],
    reduced: null,
  });
  assert.equal(decomposeVoice("만들어지"), null);
  assert.equal(decomposeVoice("쉽다"), null);
});
