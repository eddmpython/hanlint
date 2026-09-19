---
name: use-hanlint
description: 이미 쓴 한국어 마크다운을 hanlint 로 검사해 결정적 지적을 0 으로 만들 때 쓴다. 글을 쓰거나 고친 직후, 평가 루프의 0층, 발행 전 게이트가 자리다. 처음부터 쓰는 일은 write-korean 이고, 채팅 답변과 코드 주석은 대상이 아니다.
---

# hanlint 로 글 검사하기

hanlint 는 한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는다. 좋은 글인지는 판정하지
않는다. 글쓰기 규칙의 정본은 사용자 저장소의 글쓰기 스킬이고 hanlint 는 그중 기계가 잡을 수 있는 것을 집행한다.

설치는 없다. 파이썬이 있으면 `uvx hanlint`, Node 만 있으면 `npx hanlint` 다. 아래의 `hanlint` 를 그것으로 읽는다.
Claude Code에서는 PostToolUse에 `hanlint hook`, Stop에 `hanlint hook --reply`를 연결할 수 있다. 둘 다 Finding만
다음 모델 요청에 돌려주고 종료 코드 0으로 작업을 막지 않는다. 설정 JSON은 README의 같은 턴 폐루프 훅 절에 있다.

## 결과

`hanlint 글.md` 가 `집은 자리 없음` 을 내고 종료 코드 0 인 상태. 그다음에야 사람과 LLM 평가로 넘어간다.

## 순서

1. **종류를 맞춘다.** 블로그가 아니면 `--preset report|docs|guide|essay|fiction|encyclopedia` 를 붙인다. 화면의 글
   (단추, 이름표, 상태, 빈 상태) 은 `--preset screen` 이다. 소스 폴더의 화면 글을 한 표로 보려면 `hanlint sheet src/ --preset screen`. 저장소에
   `hanlint.toml` 이 있으면 그것을 따른다. 참고 문서에 `noQuestion` 이 도는 것 같은 지적은 규칙이 아니라 종류가
   안 맞는 것이다. 한 폴더에 종류가 섞여 있으면 종류마다 나눠 돌린다. `hanlint.toml` 을 만들지는 사용자가 정한다.
2. **기계가 고칠 것을 먼저 적용한다.** `hanlint fix 글.md`. 번역투, 명령형 뒤 마침표, 이중 부정, 인용이 아닌 이중
   피동을 원문에 적용하고 무엇을 바꿨는지 줄마다 보여 준다. 건너뛴 자리는 이유가 붙어 있다.
3. **남은 error 를 읽는다.** `hanlint 글.md --format compact --errors-only`. 한 줄에 지적 하나, `경로:줄 [규칙] 왜`
   꼴이고 고친 문장이 있으면 뒤에 붙는다. 기계가 읽을 때는 `--format json` 이다. 지적마다 `rule`, `line`, `quote`,
   `why` 가 있고, 고칠 수 있으면 `fix`, 좁힐 수 있으면 `candidates`, 승인 고침이 있으면 `patch` 가 붙는다.
4. **자리만 고친다.** 후보가 있으면 후보부터 읽되 기계가 골랐다고 여기지 않는다. 뜻에 맞는 것이 없으면 이름을
   직접 쓴다. `patch` 가 있으면 그 문장 전체를 `patch.after` 로 바꾼다. 어떻게 다시 쓸지 막히면
   `hanlint explain <규칙>` (왜, 어디서, 고치기, 안 잡는 것과 본보기) 과 `hanlint patterns --rule <규칙>` (error 0 이
   보장된 문장 틀) 을 본다. 그 종류의 실제 글이 그 낱말을 어떻게 쓰는지 막히면 `hanlint usage "낱말" --kind <종류>
   --format json` 을 본다. `words` 가 바로 뒤에 오는 용언과 앞뒤 명사를 문서 수로, `hits` 가 실제 문장을 준다
   (색인이 없으면 만드는 법을 알리고 2 로 끝난다. `hanlint usage kinds` 가 있는 종류를 센다. 만들지는 사용자가
   정한다). 문서 수가 많은 결합이 그 종류의 말이다. 보인 문장은 쓰임의 근거이지 정답이 아니고 사실과 숫자는 옮기지
   않는다. 지적을 없애려고 문장이나 사실을 지우지 않는다.
5. **개선한 후보만 반영한다.** 한 자리의 후보를 최대 두 번 검토한다. 같은 근거가 줄지 않거나 새 위반이 생기면
   후보를 버리고 마지막으로 보존한 원문을 유지한다. 계약이 있으면 `verify-patch`로 검증한다. 남은 error는
   원문과 함께 사람에게 넘기고 error가 없다고 말하지 않는다. notice는 자동 수정의 목표가 아니다.
6. **notice 를 한 번 읽는다.** `--severity all`. 사람 평가자와 같은 자리를 짚은 것은 `endingRepeat` 과
   `factListParagraph` 둘이었다. 그 둘을 먼저 보고 정당한 문장이면 둔다.
7. **넘긴다.** 사용자 저장소의 글쓰기 스킬이 정한 평가로 넘긴다. 평가 지적을 반영한 직후에 3 을 다시 돌린다.

## 지킬 것

- 규칙을 끄는 것은 사용자의 결정이다. 오탐이면 그 문장과 이유를 보이고, 끌지는 사용자가 `hanlint.toml` 의
  `disable` 이나 `<!-- hanlint-disable <규칙> -->` 로 정한다. 형식이 달라 줄줄이 나는 지적은 설정 키
  (`headingSentenceMaxLevel`, `ignoreFences`) 로 말하고 파일을 만들지는 사용자가 정한다.
- 이미 쓴 글이 많은 저장소에서 처음 돌리면 잠금을 먼저 묻는다. 전부 고칠지, `hanlint baseline 글들/` 로 잠그고
  새 것만 막을지는 사용자가 정한다. 잠근 뒤에는 검사에 `--baseline` 을 붙인다.
- `hanlint` 가 통과했다고 좋은 글이라고 말하지 않는다.

## 더 있는 것

절 구조가 요구사항이면 Reader Contract (`hanlint contract init`, `hanlint check`), 조직 문체와 견주려면
`hanlint profile build`, 한국어 학습자 독자면 `hanlint terms`, 승인한 고침을 다음 글에 남기려면 `hanlint learn`.
전면 개작 전에 숫자 확인표가 필요하면 `hanlint spec --preset <종류> --chars <글자 수>`를 명시적으로 부른다.
절차는 `skills/specs/start/readerContract.md` 와 `skills/specs/operation/writingAxis.md` 가 소유한다. 옵션은 파이썬 판의
`hanlint <명령> --help` 와 README 의 명령 표에 있다 (npm 판은 루트 `hanlint --help` 만 낸다).
