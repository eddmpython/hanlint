---
id: start.hanlintSkillOs
title: 이 저장소가 소유하는 것
category: start
purpose: 이 저장소의 경계와 구성, 그리고 어디로 가야 무엇이 있는지 알려준다.
whenToUse:
  - 이 저장소는 뭐하는 곳인가
  - 어디를 봐야 하나
  - 경계
  - 폴더 구조
  - cinch 와 어떻게 맞물리나
status: curated
---

# 이 저장소가 소유하는 것

## 소유하는 것

한국어 글 린터 hanlint의 코어, CLI, Python과 npm 패키지, 브라우저 편집기와 AI 사용 스킬이다.

| 경로 | 무엇 |
|---|---|
| `src/hanlint/` | 코어. 층 구조는 `operation.moduleLayers` 가 정본이다 |
| `npm/` | 파이썬의 투영. 순수 ESM, 빌드 0. `npm/src` 가 제품, `npm/test` 가 테스트, `npm/data` 는 `scripts/derive/npmData.py` 가 만든다 |
| `web/` | 같은 npm 코어를 쓰는 편집기, 개인 기록, GitHub 보관과 사용 안내. 정적 배포는 `operation.webEditor`가 소유한다 |
| `tests/` | 양방향 테스트와 구조 게이트. `tests/_attempts/` 는 실험 기록 |
| `hooks/` | 훅 판정기. `writeGate.py` 는 Claude 쓰기 훅이, `commitMessage.py` 는 git commit-msg 훅이 부른다. 얇은 셸은 `.githooks/`, 등록은 `.claude/settings.json` |
| `scripts/` | 도구. 도메인 셋이다. `derive/` 는 정본에서 파생 자료를 만들고, `fetch/` 는 외부 자료를 받고, `measure/` 는 실측 탐침이다 |
| `corpus/` | 기준 말뭉치의 카탈로그와 고정 판. 원문은 `catalogue.toml` 의 `root` (`~/.cache/hanlint/corpus/`) 에 받는다 |
| `skills/` | 운영 정본과 AI 사용 스킬 |
| `.cinch.json` | cinch 선언. 켠 스위치와 코드 뿌리의 역할. 설치된 Stop 게이트가 판정하고 `cinch status` 가 보여 준다 |
| `mainPlan/` | 끝나지 않은 기획 (추적하지 않음) |
| `memory/` | 세션 간 약속 (추적하지 않음) |

## 소유하지 않는 것

- **글의 좋고 나쁨.** 판정은 사람과 LLM 평가자가 한다. hanlint 는 세어서 확정할 수 있는 결함만 집는다
- **글쓰기 규칙의 정본.** 어떤 글이 좋은 글인지는 소비자의 글쓰기 스킬이 정한다. hanlint 는 그중
  기계가 잡을 수 있는 것을 집행할 뿐이다. 소비 저장소가 어떤 규칙을 켤지는 그 저장소의 설정이 정한다
- **맞춤법.** 공식 API 없이 비공식 스크래핑에 기대는 검사기는 넣지 않는다

## 어디로 가나

묻는 것에 따라 여는 문서가 다르다.

| 알고 싶은 것 | 어디 |
|---|---|
| 위반하면 사고가 나는 규칙 | 루트 `CLAUDE.md` (추적하지 않음) |
| 무엇을 잡고 무엇을 안 잡나 | [`start.product`](product.md) |
| 첫 검사와 프로젝트 설정 | [`start.cli`](cli.md) |
| CI와 에이전트 연결 | [`start.integrations`](integrations.md) |
| 브라우저에서 글을 고치고 기록하는 법 | [사용과 저장 안내](https://eddmpython.github.io/hanlint/guide.html) |
| 편집기 실행과 Pages 배포 | [`operation.webEditor`](../operation/webEditor.md) |
| 규칙을 더하는 법 | `operation.addingARule` |
| 커밋 전에 돌릴 것 | `operation.verify` |
| 배포 절차 | `operation.release` |
| 규칙 목록 | `hanlint rules` |
| AI 에게 글을 쓰게 하는 법 | `skills/write-korean/SKILL.md` |
| AI 에게 검사를 시키는 법 | `skills/use-hanlint/SKILL.md` |
| 바깥을 향한 소개 | 루트 `README.md` |
| 지금 진행 중인 기획 | `mainPlan/` |

## cinch 문서 역할과의 대응

cinch 는 저장소 문서를 여섯 역할로 읽는다. 이 저장소는 새 문서 나무를 만들지 않고 있는 자리를 그 역할에 댄다.

| cinch 역할 | 이 저장소의 정본 |
|---|---|
| North Star | [`start.product`](product.md) |
| 기술 명세 | [`start.readerContract`](readerContract.md), `operation.moduleLayers`, 코드 계약 (`tests/gates/layerContract.py`, `src/hanlint/data/*.schema.json`) |
| 운영 명세 | `skills/specs/operation/` |
| 이니셔티브 | `mainPlan/` (추적하지 않음. 끝나면 폴더째 지운다) |
| 세션 메모리 | `memory/` (추적하지 않음. 정본을 덮지 않는다) |
| 이벤트 원장 | Git 커밋. 형식은 `operation.sourceControl` |

## 이 저장소의 실패 방식

규칙이 늘어나는 것이다. 그럴듯한 규칙은 오탐을 낳고 오탐은 첫인상을 망친다. 그래서 실측 사례
없는 규칙을 넣지 않고, 사람 평가자가 집은 지적 가운데 hanlint 가 먼저 집었던 비율로 가치를 잰다.
규칙 수는 가치가 아니다.
