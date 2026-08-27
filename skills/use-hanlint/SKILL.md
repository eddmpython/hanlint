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
`pip install hanlint[kiwi]`. 파이썬이 없고 Node 가 있으면 설치 없이 `npx hanlint 글.md` 로 같은 검사를 한다
(지문 지도와 프로파일은 파이썬 쪽에만 있다).

## 순서

1. 글을 쓰거나 고친다.
2. `hanlint fix 글.md` 를 먼저 돌린다. 기계가 확실히 고칠 수 있는 자리 (번역투, 명령형 뒤 마침표, 이중 부정) 를
   원문에 적용하고 무엇을 바꿨는지 줄마다 보여 준다. 건너뛴 자리는 이유가 붙어 있으니 손으로 고친다.
3. `hanlint 글.md --format compact --errors-only` 를 돌린다. 한 줄에 지적 하나다. `경로:줄 [규칙] 왜` 꼴이고
   고친 문장이 있으면 뒤에 붙는다. 글이 파일이 아니라 손에 있으면 `hanlint - --path 이름.md` 로 stdin 에 넣는다.
   첫 줄은 어느 설정을 읽었는지고 마지막 줄은 요약이다. 기계가 읽을 때는 `--format json` (지적마다 `rule`,
   `line`, `quote`, `why`, 고칠 수 있으면 `fix` 와 `fragment`, `replacement`).
4. `error` 를 전부 고친다. 규칙이 왜 있는지 모르면 `hanlint explain <rule>` 을 읽는다. 네 절 (왜, 어디서,
   고치기, 안 잡는 것) 이 있다.
5. 마지막에 한 번 `--severity all` 로 `notice` 를 읽고 판단한다. 사실 나열 (factListParagraph) 과 흐름 끊김
   (topicBreak) 은 이유 문장을 넣어 잇는 것이 대체로 답이다. 정당한 문장이면 둔다.
6. 3 으로 돌아가 `error` 가 0 이 될 때까지 반복한다. 보통 두 번이면 끝난다.
7. 글의 모양을 보려면 `hanlint audit 글.md`. 지문 지도에서 색이 있는 자리가 구멍이다. 점수는 없다.
8. 0 이 되면 사용자 저장소의 글쓰기 스킬이 정한 평가로 넘어간다.

## 지킬 것

- 지적을 없애려고 문장을 지우지 않는다. 사실과 실행 단계는 자르지 않는다.
- 규칙을 끄는 것은 사용자의 결정이다. 오탐이라고 판단되면 그 문장과 이유를 사용자에게 보이고, 끌지는 `hanlint.toml`
  의 `disable` 로 사용자가 정한다. 규칙이 맞지만 그 자리만 예외일 때 (상투어를 인용하는 문단) 는 그 문단 앞뒤에
  `<!-- hanlint-disable cliche -->` 와 `<!-- hanlint-enable cliche -->` 를 두고, 왜 예외인지 사용자에게 말한다.
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
