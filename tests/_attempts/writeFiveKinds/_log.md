# 다섯 종류의 글을 직접 써서 검사해 본 기록 (2026-08-28)

fixture 는 구현이 의도대로 도는지를 증명하지 **쓰는 사람이 실제로 쓸 만한지**를 증명하지 않는다.
그래서 글을 다섯 편 새로 쓰고, `skills/use-hanlint/SKILL.md` 의 순서를 글자 그대로 밟았다.

## 대상

hanlint 를 의식하지 않고 평소 쓰던 대로 먼저 썼다. 종류를 일부러 갈랐다.

| 글 | 종류 | 맞는 프리셋 |
|---|---|---|
| 1blog.md | 기술 경험담 | blog |
| 2docs.md | 설정 명세 | docs |
| 3report.md | 측정 보고서 | report |
| 4essay.md | 짧은 에세이 | blog |
| 5tutorial.md | 단계별 안내 | blog |

## 1바퀴: 기본값으로 그냥 돌렸을 때

error 15, notice 15 였다.

| 심각도 | 분포 |
|---|---|
| error | noQuestion 4, danglingDeixis 4, cliche 2, nounPile 1, sectionNoProse 1, deixis 1, headingSentence 1, headingUniform 1 |
| notice | factListParagraph 6, readerAbsent 4, topicBreak 3, endingRepeat 2 |

## 마찰 넷

이 탐침이 실제로 알아낸 것이다. 셋은 그 자리에서 고쳤다.

### 1. 다음 걸음이 가장 작은 더미를 가리켰다

`다음: error 15건을 고친다. 다시 쓸 틀은 hanlint patterns --rule cliche` 가 나왔다. cliche 는 2건이고
가장 많은 것은 noQuestion 4건이었다. `sorted({...})[0]` 이라 알파벳 첫 이름을 골랐던 것이다.
한 줄뿐인 안내가 15건 가운데 2건을 가리키고 있었다. **고쳤다.** 가장 많이 난 규칙을 고르고 같은 수면
이름 순으로 가른다.

### 2. lint 에 `--preset` 이 없었다

2docs.md 와 3report.md 는 문서와 보고서인데 blog 로 돌아 `noQuestion` 과 `readerAbsent` 가 8건 났다.
그런데 `--config`, `--disable`, `--analyzer` 는 다 있는데 프리셋만 옵션이 없었다. 스킬은
`hanlint init --preset docs` 를 시켰다. **글 한 편을 검사하려고 남의 저장소에 파일을 만들라는 뜻이다.**
한 폴더에 종류가 섞이면 설정 파일 하나로는 애초에 못 푼다. **고쳤다.** `--preset` 을 공용 옵션에 넣었고
머리줄이 지금 도는 프리셋을 말한다 (`설정: 기본값, 프리셋 docs`).

### 3. `에 대한` 이 번역투 사전에 없었다

`이 방식의 문제점에 대한 이해가 필요합니다` 를 썼는데 안 잡혔다. 사전에 `에 대(?:해|하여|해서)` 는
있고 관형형 `에 대한` 이 없었다. 관형형이 서술형보다 흔하다. `config/settings.py` 의 설정 예시가
`translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]` 인 것이 이미 구멍의 증거였다.
**고쳤다.** `에 대한` 과 `에 관한` 을 사전에 넣고 fixture 에 짝으로 박았다. 이 저장소 문서 16편에
새로 나는 지적은 0건이다.

### 4. 본보기가 잘려서 다시 쳐야 했다

text 출력의 본보기 줄이 `…` 로 잘린다. headingUniform 의 고친 뒤가 잘려서 `hanlint explain` 을 또
쳤다. **안 고쳤다.** 한 줄에 규칙 하나를 지키려면 잘라야 하고, 전문은 `explain` 이 소유한다. 다만
잘렸다는 것과 어디서 전문을 보는지를 알리는 것이 나은지는 다음에 잰다.

## 2바퀴: 고친 뒤

프리셋을 맞춰 다시 돌리니 error 14 였다 (프리셋이 8건을 걷어냈다). 전부 참이었고 손으로 고쳤다.

| 글 | 남은 error | 무엇 |
|---|---|---|
| 1blog.md | 7 | noQuestion, danglingDeixis 2, translationese, nounPile, cliche 2 |
| 2docs.md | 1 | sectionNoProse (표만 있는 절) |
| 3report.md | 1 | deixis (`해당 기능은`) |
| 4essay.md | 2 | headingSentence, danglingDeixis |
| 5tutorial.md | 3 | headingUniform, noQuestion, danglingDeixis |

전부 고쳐 다섯 편 모두 error 0 이 됐다. **두 바퀴로 끝났다.** 스킬이 말하는 "보통 두 번이면 끝난다" 와
맞는다.

## 본보기가 실제로 한 일

고칠 때 본보기를 그대로 썼다. 특히 둘이 값졌다.

- `headingUniform`: `## 값 넣기` 를 `## 값은 어디에 넣나` 로 바꾸는 꼴을 보여 준다. 어미를 섞으라는
  말만으로는 무엇을 어떻게 섞을지 알 수 없다
- `danglingDeixis`: `이것을 실행합니다` 를 `make_qr.py 를 실행합니다` 로. 이름을 쓰라는 말의 뜻이
  한 줄로 보인다

세 번 나온 `이것을` 을 전부 이름으로 바꿀 수 있었던 것은 본보기 덕이다.

## 안 나온 것

다음은 잡히길 기대했는데 안 잡혔다. 여기 적어 두되 규칙으로 만들지는 않았다. 실측 사례가 한 편뿐이라
근거가 얇고, 확정 치환이 되는 것도 아니다.

| 문장 | 왜 안 만들었나 |
|---|---|
| 테스트를 진행하도록 하겠습니다 | `~도록 하겠습니다` 는 군말이지만 정당한 자리 (사동) 와 표층으로 안 갈린다 |
| 확인이 요구됩니다 | `요구되다` 가 정당한 문서 표현인 자리가 있다 |
| 속도 향상이 이루어졌습니다 | `이루어지다` 도 마찬가지다 |
| 성능이 크게 개선되었습니다 | `크게` 가 얼마인지 없는 것은 뜻의 문제라 기계가 못 본다 |

## 다음에 잴 것

- 한 폴더에 종류가 섞였을 때. 지금은 `--preset` 을 파일 수만큼 나눠 쳐야 한다. 실제 저장소가
  `docs/` 와 `blog/` 로 갈려 있는지, 섞여 있는지를 형제 저장소들에서 세어 본다
- 본보기의 `…` 잘림이 실제로 사람을 explain 으로 보내는지
