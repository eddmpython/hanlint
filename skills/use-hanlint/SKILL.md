---
name: use-hanlint
description: 한국어 마크다운 글을 hanlint 로 검사해 지적을 0건으로 만든 뒤 사람이나 LLM 평가로 넘긴다. 글을 쓰거나 고친 직후, 평가 루프의 0층, 발행 전 게이트에 쓴다. 규칙이 왜 있는지는 hanlint explain 이 답한다.
---

# hanlint 로 글 검사하기

hanlint 는 한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는다. 좋은 글인지는 판정하지
않는다. 이 스킬은 글쓰기 규칙을 복사하지 않는다. 글쓰기 규칙의 정본은 사용자 저장소의 글쓰기 스킬이고,
hanlint 는 그중 기계가 잡을 수 있는 것을 집행한다.

## 결과

`hanlint 글.md` 가 `집은 자리 없음` 을 내고 종료 코드 0 인 상태. 그다음에야 사람과 LLM 평가로 넘어간다.

## 먼저 확인

```powershell
hanlint --version
```

없으면 사용자에게 설치 명령을 보인다. `pip install hanlint`. 의존성은 없다. 형태소 정밀 모드가 필요하면
`pip install hanlint[kiwi]`.

## 순서

1. 글을 쓰거나 고친다.
2. `hanlint 글.md --format json` 을 돌린다. 지적마다 `rule`, `line`, `quote`, `why` 가 있고 기계가 고칠 수 있는
   것은 `fix` 가 있다. `severity` 가 `error` 인 것은 규칙 위반이고 `notice` 는 확인이 필요한 것이다.
3. `error` 를 전부 고친다. `fix` 가 있으면 그대로 쓴다. 규칙이 왜 있는지 모르면 `hanlint explain <rule>` 을
   읽는다. 네 절 (왜, 어디서, 고치기, 안 잡는 것) 이 있다.
4. `notice` 는 읽고 판단한다. 사실 나열 (factListParagraph) 과 흐름 끊김 (topicBreak) 은 이유 문장을 넣어
   잇는 것이 대체로 답이다. 정당한 문장이면 둔다.
5. 2 로 돌아가 `error` 가 0 이 될 때까지 반복한다. 보통 두 번이면 끝난다.
6. 글의 모양을 보려면 `hanlint audit 글.md`. 지문 지도에서 색이 있는 자리가 구멍이다. 점수는 없다.
7. 0 이 되면 사용자 저장소의 글쓰기 스킬이 정한 평가로 넘어간다.

## 지킬 것

- 지적을 없애려고 문장을 지우지 않는다. 사실과 실행 단계는 자르지 않는다.
- 규칙을 끄는 것은 사용자의 결정이다. 오탐이라고 판단되면 그 문장과 이유를 사용자에게 보이고, 끌지는 `hanlint.toml`
  의 `disable` 로 사용자가 정한다.
- `hanlint` 가 통과했다고 좋은 글이라고 말하지 않는다. 세어서 잡히는 결함이 없다는 뜻뿐이다.

## 실패할 때

- `찾지 못했다`: 경로를 확인한다. 마크다운 파일 하나가 인자다.
- `kiwipiepy 가 없다`: `--analyzer surface` 로 돌리거나 `pip install hanlint[kiwi]`.
- `모르는 설정 키`: `hanlint init` 이 만드는 파일의 키만 쓴다.

## 참고

- 규칙 목록: `hanlint rules`
- 설정 만들기: `hanlint init`
- 지문 계층 JSON: `hanlint print 글.md`. 다른 도구가 지문 위에 무엇을 얹을 때
- 문체 프로파일: `hanlint profile build 승인된글들/` 뒤 `hanlint 글.md --profile profile.json`
