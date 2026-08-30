# hanlint

[![PyPI](https://img.shields.io/pypi/v/hanlint?label=pypi)](https://pypi.org/project/hanlint/)
[![npm](https://img.shields.io/npm/v/hanlint?label=npm)](https://www.npmjs.com/package/hanlint)
[![CI](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml/badge.svg)](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/hanlint)](https://pypi.org/project/hanlint/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**한국어 글쓰기 검사 도구 (Korean prose linter).** 마크다운 원고에서 번역투, 명사 나열, 이중 피동,
가리킬 것 없는 지시어, 조각난 문단처럼 **세면 확정되는 결함**을 찾아 자리와 이유와 다시 쓴 본보기를 준다.
맞춤법 검사기가 아니다. 맞춤법이 맞는데도 안 읽히는 글을 잡는 문장과 문단의 린터다.

파이썬과 npm 두 판이고 런타임 의존성이 없다. 블로그 원고, 기술 문서, 보고서, AI 가 쓴 초안을 발행 전에
게이트로 막는 자리에 쓴다.

```powershell
pip install hanlint      # 파이썬이 없으면 npx hanlint 글.md
hanlint 글.md
```

## 읽기 쉬운 글이란 무엇인가

읽기 쉬운 글은 쉬운 내용을 다룬 글이 아니다. **독자가 문장을 머릿속에서 다시 번역하지 않아도 되는 글**이다.
어려운 내용도 그렇게 쓸 수 있고, 쉬운 내용도 그렇게 못 쓸 수 있다.

독자가 다시 번역하게 만드는 자리는 정해져 있다. 아래 왼쪽을 읽으면 뇌가 한 번 멈춘다.

| 독자가 멈추는 문장 | 바로 읽히는 문장 |
|---|---|
| 가상환경 생성 후 패키지 설치 확인 절차를 따릅니다 | 가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다 |
| 이 기능을 통해 파일 생성이 가능합니다 | `저장` 버튼을 누르면 `report.csv` 가 만들어집니다 |
| 결과가 저장되어집니다 | 결과가 저장됩니다 |
| 표를 엽니다. 이것을 고칩니다 | 표를 엽니다. `금액` 열의 값을 고칩니다 |
| 병합 셀은 첫 칸에만 값이 있습니다. 나머지는 빈값입니다. 정렬하면 순서가 깨집니다 | 병합 셀은 첫 칸에만 값이 들어 있고 나머지는 비어 있습니다. 그대로 정렬하면 빈 칸이 값과 떨어져 순서가 깨집니다 |

왼쪽이 나쁜 까닭은 취향이 아니다. 각각 **독자에게 일을 떠넘긴다.** 첫째는 조사를 끼워 넣게 하고, 둘째는
무엇을 눌러 무엇이 생기는지 짐작하게 하고, 셋째는 같은 뜻을 두 겹으로 읽게 하고, 넷째는 스크롤을 되돌리게
하고, 다섯째는 세 문장 사이의 관계를 독자가 직접 세우게 한다.

이 다섯 가지에는 공통점이 하나 더 있다. **전부 세어서 확정된다.** 명사가 몇 개 이어졌는지, 피동이 몇 겹인지,
지시어가 가리킬 것이 앞 문장에 있는지, 문단에 인과 표지가 하나라도 있는지는 읽지 않고도 셀 수 있다.

hanlint 는 그 셀 수 있는 것만 맡는다. 재미있는지, 설득력이 있는지, 검색해 들어온 독자가 원하던 답을
받았는지는 판정하지 않는다. 그것은 사람과 LLM 평가자가 더 잘한다. 그래서 맞춤법 검사기와도 겹치지
않는다. 맞춤법 검사기는 낱말이 틀렸는지 보고 hanlint 는 문장과 문단이 독자에게 일을 떠넘기는지 본다.

## hanlint 가 한국어 글에서 잡는 것

지적마다 **자리, 이유, 그리고 이렇게 쓴다는 본보기**를 준다. 세 번째가 이 도구의 핵심이다.

```text
설정: hanlint.toml

글.md  집은 자리 2, 확인할 자리 1

글.md:12  [doublePassive]
  결과가 저장되어집니다.
  되어지 는 이중 피동이다. 피동 하나로 줄인다
  고친 뒤: 결과가 저장됩니다.

글.md:31  [nounPile]
  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
  명사 5개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. 동사로 되돌린다

본보기 (고치기 전, 고친 뒤)
  [doublePassive]
    전  결과가 저장되어집니다.
    후  결과가 저장됩니다.
  [nounPile]
    전  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
    후  가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다.

후보 (기계가 고르지 않음)
  [doublePassive] 결과가 저장되어집니다.
    - 결과가 저장됩니다. (`되어지`의 피동 겹을 하나로 줄인다)

다음: error 2건 가운데 1건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다
```

**왜 본보기인가.** 실제 발행된 글 다섯 편에 돌려 재 봤다. 지적 104건 가운데 기계가 자동으로 고칠 수 있는
것은 0건이었다. 나머지 100%는 "무엇이 틀렸다"만 듣고 "그럼 어떻게 쓰나"는 글쓴이가 알아서 해야 했다.
금지 목록은 사람을 고치게 만들지 못한다. 그래서 규칙마다 실제로 검증된 전후 짝을 달았고, 지금은
그 104건 전부에 본보기가 붙는다. 재는 방법과 숫자는 [tests/_attempts/fixReach/](tests/_attempts/fixReach/)
에 있다.

본보기는 장식이 아니라 **검증된 데이터**다. `before` 는 그 규칙에 실제로 잡히는 글이고 `after` 는 같은 뜻인데
안 잡히는 글이며, 게이트가 매번 둘 다 돌려 확인한다. 안내가 틀리면 나쁜 글이 퍼지기 때문이다.

### 본보기가 그 글의 말투를 따른다

규칙마다 둔 기본 본보기 54개와 문형 10개는 데이터에 합니다체 한 벌만 둔다. lint 와 watch 가 글의 종결을 세어 합니다체,
한다체, 해요체 가운데 하나로 바꿔 보여 준다. 한다체 명세에 `확인합니다` 라고 남의 말투로 고치라고 하지
않는다. `hanlint explain <규칙> --register 한다` 와 `hanlint patterns --register 해요` 로 문체를 직접
고를 수도 있다.

같은 결함도 글의 종류에 따라 풀어 쓰는 법이 다르면 문맥 본보기를 고른다. 지금 `nounPile` 은 기본 절차문,
보고서, 기술 문서와 백과에 서로 다른 짝을 두어 모두 56개다. `--preset report` 로 검사한 보고서에는 사업
이름의 관계를 푼 짝이 나오고, `--preset docs` 에는 기술 용어를 남긴 채 실패 조건과 행동을 푼 짝이 나온다.
어느 짝이든 고치기 전은 잡히고 고친 뒤는 모든 error 가 0인지 세 문체에서 게이트가 확인한다.

### 고친 글에서 프로젝트 본보기를 배운다

`hanlint learn 전.md 후.md` 는 글쓴이가 실제로 고쳐서 지적이 사라진 문장 짝을 후보로 낸다. 여러 문장을
한꺼번에 다시 쓴 모호한 구간은 추측하지 않는다. 출력은 제안일 뿐이며, 사람이 뜻을 확인한 것만
`hanlint.toml` 의 `[[exemplars]]` 에 승인한다. 프로젝트 본보기는 같은 규칙과 프리셋의 내장 본보기를
덮어쓰므로 이후 lint, rules, explain 과 JSON 출력에서 조직이 실제로 쓰는 고침을 보여 준다.

```console
hanlint learn 전.md 후.md
hanlint learn 전.md 후.md --format toml
```

### AI에 작문 근거를 한 번에 건넨다

`hanlint packet 글.md`는 원문, 현재 지문, 독자 상태, 같은 종류의 편집 글 분포, 실제 지적, 선택된 본보기,
검증된 문형을 `hanlint.writingPacket` JSON 하나로 묶는다. 생성 모델이 바뀌어도 근거는 같다. 처음부터
쓸 때는 `--purpose draft`, 초안을 고칠 때는 `--purpose revise`를 쓴다. 말뭉치 문장을 검색해 복사하지 않고
분포와 전후 변환만 전달하므로 공통 AI 문체로 평준화하는 위험도 줄인다.

```console
hanlint packet 요구.md --purpose draft --preset docs
hanlint packet 초안.md --purpose revise --output packet.json
```

실행 절차는 [write-korean 스킬](skills/write-korean/SKILL.md)에 있다. 원문 전문을 JSON에 넣지 않으려면
`--no-source`를 붙인다.

이 변환은 형태소 분석기를 넣지 않은 작은 형태 층이 맡는다. 조사 맞추기, 종결 어미의 어간과 시제와 서법,
피동과 사동을 따로 다룬다. 기준 말뭉치 390편, 17,420문장에서 합니다체 1,992개는 전부, 한다체 12,255개는
12,209개를 원문 그대로 다시 만들었다. 그렇게 확인한 활용형 14,201개는 세 문체를 모두 만든다. 해요체
원문을 거꾸로 푸는 일은 표층만으로 확정되지 않아 범위에 넣지 않았다.

### 고를 수 있을 만큼만 후보를 낸다

`--format json` 의 지적에는 만들 수 있을 때만 `candidates` 가 붙는다. 각 후보는 문장 `text` 와 왜 만든
것인지 적은 `why` 를 가진다. 기계는 고르지 않는다. 현재 내보내는 후보는 세 종류다.

- 이중 피동을 한 겹으로 줄인 문장
- 긴 문장을 끊어 볼 연결 어미 뒤
- 지시어가 가리킬 수 있는 앞 문장의 명사

범위는 말뭉치에서 재고 사람이 실제 문맥을 읽어 골랐다. 후보를 시험한 지적은 1,498건이고 규칙마다 10건씩
50건을 검토했다. 장문과 지시어 후보는 각각 10건 중 7건, 이중 피동은 10건 전부 골랐다. 명사 나열은 1건,
종결 어미 반복은 0건이라 제품에서 뺐다. 다섯 종류의 새 글을 쓴 3회차에서는 첫 검사 error 14, notice 6에
후보 14개가 나왔고, 두 번 고친 뒤 다섯 편 모두 error 0, notice 0이었다.

## 설치와 첫 검사, 30초

```powershell
pip install hanlint
hanlint
```

인자 없이 치면 첫 화면이 나온다. 지금 이 폴더에 있는 마크다운 이름으로 만든 예시가 거기 있다.

```text
hanlint 0.0.7  한국어 글에서 세면 확정되는 결함을 집는다. 좋은 글인지는 판정하지 않는다

  hanlint 초안.md        검사한다. 자리와 이유와 고칠 말이 나온다
  hanlint fix 초안.md    기계가 확실히 고칠 수 있는 자리를 원문에 적용한다
  hanlint audit 초안.md  글의 모양을 지도와 분포로 본다

이 폴더의 마크다운: 초안.md. 폴더를 통째로 줘도 된다 (hanlint .)
```

그다음은 셋만 알면 된다.

| 하고 싶은 것 | 치는 것 |
|---|---|
| 이 글에 무엇이 잘못됐나 | `hanlint 글.md` |
| 기계가 고칠 수 있는 것은 먼저 고쳐 줘 | `hanlint fix 글.md` |
| 쓰는 동안 계속 봐 줘 | `hanlint watch 글.md` |

`npx hanlint 글.md` 는 설치 없이 같은 검사를 한다. 폴더를 주면 그 아래 마크다운을 찾되 점으로 시작하는
폴더와 `node_modules` 에는 안 들어간다. 그 안을 보려면 그 폴더를 직접 준다.

## 글의 종류를 고른다: 블로그, 보고서, 문서

기본은 블로그다. 독자를 부르고 절마다 눈에 보이는 결과를 남기는 글이 기준이라, 보고서나 참고 문서에
그대로 대면 맞지 않는 지적이 나온다. 그때는 규칙을 하나씩 끄지 말고 종류를 고른다.

```powershell
hanlint 명세.md --preset docs      # 이번 검사에만
hanlint init --preset docs         # 저장소에 고정할 때
```

| 프리셋 | 누구를 위한 것 | 끄는 것 |
|---|---|---|
| `blog` | 독자를 부르고 절마다 결과를 남기는 글 | 없다 |
| `report` | 보고서 | 독자 호출과 절 결과 요구 다섯 |
| `docs` | 참고 문서, 명세, README | 위에 더해 검증 기록과 그림용 펜스 둘 |

`--preset` 은 설정 파일 없이 이번 실행에만 정한다. 남의 저장소에 파일을 만들지 않고 문서 한 편을
검사할 때 쓴다. 한 폴더에 종류가 섞여 있으면 종류마다 나눠 돌린다. 지금 무엇이 켜져 있는지는
`hanlint doctor` 가 한 화면으로 답한다.

### 같은 종류의 편집된 글과 견준다

프리셋은 규칙만 고르지 않는다. 블로그, 보고문, 기술 문서, 단계별 안내, 수필, 소설, 백과의 기준
프로파일도 고른다. 프로파일은 재사용 조건과 판본을 고정한 글 1,600편, 문장 144,214개에서 문장 길이,
쉼표 수, 새 화제 수, 유보 표현 수의 분포를 센 작은 표다. 원문은 제품에 싣지 않는다.

`outsideProfile` 은 그 종류 문장의 99% 밖에 있는 자리만 notice 로 낸다. "문장 길이 47어절, 보고문
3,897문장 가운데 상위 0.8%"처럼 관찰한 사실을 말할 뿐 고치라고 명령하거나 글을 채점하지 않는다.
프리셋이 틀리면 대조도 틀리므로 종류가 섞인 폴더는 나눠 돌린다. 조직에서 승인한 글의 문체가 더 중요한
때는 그 글들로 프로파일을 바꾼다.

```powershell
hanlint profile build 승인된글들/ --output 우리문체.json
hanlint 새글.md --profile 우리문체.json
```

### 한국어 학습자에게 처음 풀어 쓸 낱말을 찾는다

한국어 학습자가 독자라면 파이썬 판의 `terms` 를 한 번 더 돌린다. 국립국어원의 한국어 학습용 어휘
5,965개를 A, B, C로 나눈 원 자료와 화제어의 첫 등장을 맞댄다.

```powershell
hanlint terms 글.md
hanlint terms 글.md --outside --format json
```

기본 출력은 여러 뜻이 모두 C에 속하는 화제어만 보인다. A/C처럼 동형어의 등급이 갈리면 C라고 단정하지
않는다. `--outside` 는 목록 밖 한글 화제어도 내지만 최신 전문어와 고유명사를 가르지 못하므로 후보일
뿐이다. 이 등급은 한국어 학습자를 위한 것이며 한국어 모어 화자의 낱말 난도나 글의 품질 점수가 아니다.
자료원, 필드, 인코딩, 라이선스, 한계는
[`learningVocabularySource.toml`](src/hanlint/data/learningVocabularySource.toml)이 소유한다.

## 이미 쓴 글이 많은 저장소에 들일 때

새 도구를 이미 쌓인 문서에 대면 첫날 지적이 쏟아진다. 실측이다. 남의 저장소 문서 여섯 편에 그냥 돌리면
error 가 21건 나왔다. 규칙이 틀려서가 아니라 그 글들이 실제로 문단이 조각나 있고 제목이 문장이기
때문이다. 그런데 첫날 21건을 보는 팀은 도구를 끈다.

그래서 **지금 있는 것을 잠그고 새로 생긴 것만 막는다.**

```powershell
hanlint baseline 글들/          # .hanlint-baseline.json 을 만들어 커밋한다
hanlint 글들/ --baseline        # 그다음부터 새로 생긴 지적만 나온다
```

잠금은 줄 번호가 아니라 **인용문**으로 건다. 코드 린터는 파일과 줄로 잠그지만 글은 문단 하나만 고쳐도
아래 줄 번호가 전부 밀려 잠근 것이 풀린다. hanlint 는 지적이 인용문을 들고 있어서 글자로 잠글 수 있고,
그래서 성질 하나가 따라온다.

| 글에 한 일 | 잠금이 하는 일 |
|---|---|
| 문단을 옮겨 줄 번호가 밀렸다 | 그대로 잠겨 있다. 헛경보가 안 난다 |
| 잠긴 문장을 고쳤다 | 새 지적이 된다. 손댔으면 책임진다 |
| 문장을 지웠다 | `hanlint baseline 글들/ --prune` 이 죽은 잠금을 치운다 |
| 새 문장을 썼다 | 잠금과 무관하게 잡힌다 |

**손댄 자리만 막는다.** 기한도 비율도 정하지 않아도 글을 고칠 때마다 잠금이 줄어든다. 잠금 파일은 사람이
읽는 JSON 이라 PR 에서 무엇이 잠겼는지 보이고, `hanlint doctor` 가 몇 건이 잠겨 있는지 늘 말한다. 빚을
감추는 자리가 되지 않게 하려는 것이다.

## 잘 읽히는 글을 쓰는 법

규칙은 결국 다섯 가지를 말한다. 각 항목의 오른쪽이 hanlint 가 그것을 세는 방식이다.

### 1. 명사를 쌓지 말고 동사로 되돌린다

한국어는 조사가 관계를 표시한다. 명사만 이어 붙이면 그 표시가 사라지고 독자가 조사를 스스로 끼워 넣는다.

| 고치기 전 | 고친 뒤 |
|---|---|
| 가상환경 생성 후 패키지 설치 확인 절차를 따릅니다 | 가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다 |
| 회사의 팀의 결정의 근거를 봅니다 | 그 팀이 왜 그렇게 정했는지 근거를 봅니다 |

아래쪽처럼 한 문장에 관형격 조사가 셋 이상 나오는 것도 같은 병이라 `nounPile` 과 `euiChain` 이 함께 센다.

### 2. 독자가 누르고 입력할 것을 이름으로 쓴다

가리키는 말은 전부 스크롤을 되돌리게 만든다. 특히 가리킬 대상이 앞 문장에 아예 없으면 독자는 되돌아가도
못 찾는다.

| 고치기 전 | 고친 뒤 |
|---|---|
| 터미널을 엽니다. 이것을 실행합니다 | 터미널을 엽니다. `make_qr.py` 를 실행합니다 |
| 해당 값을 위의 코드에 넣습니다 | `행 수` 칸에 100을 넣습니다 |

그래서 `deixis` 는 가리키는 말을, `danglingDeixis` 는 그중 앞 문장에 대상이 없는 것을 따로 센다.

### 3. 사실을 나란히 놓지 말고 이유로 잇는다

독자는 낱말이 아니라 문장 사이의 이유를 못 따라가서 멈춘다. 짧은 평서문 셋을 붙여 놓으면 그 관계를
독자가 세운다.

> 고치기 전: 병합 셀은 첫 칸에만 값이 있습니다. 나머지 칸은 빈값입니다. 정렬하면 순서가 깨집니다
>
> 고친 뒤: 병합 셀은 첫 칸에만 값이 들어 있고 나머지는 비어 있습니다. 그대로 정렬하면 빈 칸이 값과
> 떨어져 순서가 깨집니다

오른쪽이 더 길지만 읽는 시간은 짧다. `factListParagraph` 가 인과 표지 없는 문단을, `endingRepeat` 이
이유도 질문도 없이 같은 어미만 이어지는 구간을 센다.

### 4. 글 전체의 자기모순

그럼 hanlint 는 맞춤법 검사기와 무엇이 다를까요? 갈리는 자리가 여기다. 문장 하나만 보면 멀쩡한데
**두 자리를 맞대 보면 틀린 것**이 있고, 그것은 글 전체를 들고 있어야 보인다.

- 도입은 `여섯 가지` 라 했는데 결말은 `다섯 가지` 라 센다 (`countMismatch`)
- `뒤에서 다루겠습니다` 라 해 놓고 끝까지 안 나온다 (`promiseRecall`)
- 만들지 않은 파일을 뒤에서 읽는다 (`inputFileSource`)
- 설치 줄에 없는 패키지를 import 한다 (`installImport`)
- 표의 한 열에서 한 칸만 다른 잣대로 쟀다 (`tableOddCell`)
- `453MB 에서 700MB 로 올라갔습니다` 인데 453MB 가 앞에 한 번도 안 나왔다 (`numberOrphan`)

따라 하는 독자는 이런 자리에서 실제로 멈춘다. 문장이 예뻐도 소용이 없다.

### 5. 독자를 부르고 절마다 결과를 남긴다

물음표가 한 번도 없는 글은 독자에게 한 번도 말을 걸지 않은 글이다. 한 절을 다 읽었는데 자기 화면에서
확인할 것이 없으면 그 절은 과정이 아니라 참고 자료다.

| 고치기 전 | 고친 뒤 |
|---|---|
| 파일을 만들 수 있습니다 | 터미널에 `dir` 을 쳐서 파일 이름을 확인해 봅니다 |
| 표가 어디에 생기는지 설명합니다 | 그럼 표는 어디에 생겼을까요? 실행한 폴더에 있습니다 |

`noQuestion` 과 `sectionResult` 가 독자를 부르는 자리를 세는데, 보고서와 참고 문서는 그 계약을 지지
않으므로 `report` 와 `docs` 프리셋이 둘을 끈다.

규칙 하나가 왜 있는지와 그 본보기는 `hanlint explain <규칙>` 이 전부 보여 준다.

### 다시 쓸 틀

위 다섯 가지를 **빈칸이 있는 틀**로도 든다. 본보기가 고친 사례 하나라면 문형은 그 사례를 다시 쓸 수 있는
틀이다. 지적을 받았는데 어떻게 다시 쓸지 모를 때 그 규칙을 피하는 틀만 골라 본다.

```powershell
hanlint patterns --rule nounPile
```

```text
동사로 되돌리기  (nounPile 를 피한다)
  틀    {무엇}을 {한 뒤} {무엇}이 {어떤지} {확인합니다}
  언제  명사가 셋 이상 이어질 때. 조사를 되살려 무엇이 무엇의 목적어인지 보인다
  예시  가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다.
  대신  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
  출처  이오덕 우리글 바로쓰기의 명사문을 동사문으로
```

열 개가 있다. 행동과 결과, 확인, 인과 잇기, 이름으로 이어받기, 독자에게 묻기, 값 소개, 동사로 되돌리기,
결핍 도입, 수치 비교, 미룬 것 회수다. 출처는 글쓰기 스킬과 한국 글쓰기 책들 (이오덕 `우리글 바로쓰기`,
이수열 `우리말 우리글 바로 쓰기`, 김정선 `내 문장이 그렇게 이상한가요`, 배상복 `문장기술`) 이다.

**예시는 전부 hanlint 를 error 0 으로 통과한다.** 게이트가 매번 확인하므로 규칙이 바뀌어 틀이 낡으면
빨갛다. 통과가 보장된 틀이라는 것이 이 명령이 파는 것이다.

책들의 조언을 규칙으로 넣으려고 실측했더니 대부분 규칙이 아니었다. 김정선이 든 `것` 은 발행본 다섯
편에서 75건이 걸리는데 표본이 전부 정당했다. 그 조언들은 "이건 틀렸다" 가 아니라 "이 자리를 다시 보라"
는 교정자의 눈이다. 금지로는 못 담고 틀로는 담긴다. 재는 방법과 숫자는
[tests/_attempts/koreanStyleBooks/](tests/_attempts/koreanStyleBooks/) 에 있다.

## AI 초안 검사

AI 가 쓴 한국어는 대체로 문법이 맞고 대체로 밋밋하다. 위 다섯 가지를 정확히 어긴다. 명사를 쌓고, 지시어를
쓰고, 사실을 나란히 놓고, 도입에서 약속한 개수를 결말에서 잊고, 독자를 한 번도 부르지 않는다.

그래서 AI 에게 규칙을 말로 설명하는 대신 **기계가 읽는 지적을 그대로 준다.**

```powershell
hanlint 글.md --format json
```

지적마다 `rule`, `line`, `quote`, `why` 가 오고 그 뒤에 `exemplar` 가 붙는다. `before` 와 `after` 와
`moved` 셋이다. AI 는 규칙 이름과 금지 사유뿐 아니라 검증된 변환 한 쌍을 받는다. 실제 수정 성공률이
높아지는지는 [exemplarLift 탐침](tests/_attempts/exemplarLift/)의 짝실험으로 따로 잰다.

에이전트에 붙일 때는 [skills/use-hanlint/SKILL.md](skills/use-hanlint/SKILL.md) 를 스킬 폴더에 둔다.
글을 쓴 직후 스스로 검사하고 error 가 0 이 될 때까지 고친 뒤에 사람에게 넘긴다.

## 평가 루프에서의 자리

hanlint 는 **0층**이다. 좋은 글인지는 판정하지 않는다.

```text
쓴다
 ↓
0층  hanlint            결정적. 고치면 확실히 0 이 된다. 0 이 될 때까지 여기서만 돈다
 ↓
1층  규칙 위반 (LLM)     기계가 못 재는 규칙만 남는다
2층  규칙 밖 읽힘 (LLM)  지루한가, 몰입이 끊기는가, 검색 의도에 답하는가
 ↓
지적 없음 → 끝
```

블로그 글 한 편을 LLM 평가자 넷이 네 라운드 읽었더니 지적이 31, 27, 40, 16 건으로 줄지 않았다. 마지막
16건의 절반이 세면 잡히는 것이었다. 평가자는 라운드마다 다른 것을 발견하므로 셀 수 있는 것에 화력을 쓰면
루프가 수렴하지 않는다. 0층이 바닥을 깔아야 위층이 자기 일을 한다.

## 명령 한눈에

| 명령 | 무엇 |
|---|---|
| `hanlint` | 첫 화면. 이 폴더의 파일 이름으로 만든 예시와 다음 걸음 |
| `hanlint 글.md` 또는 `hanlint 글들/` | 검사한다. 폴더면 그 아래 마크다운 전부 |
| `hanlint watch 글.md` | 저장할 때마다 다시 검사한다 |
| `hanlint fix 글.md` | 번역투, 명령형 뒤 마침표, 이중 부정처럼 확실한 자리를 고친다 |
| `hanlint explain <규칙>` | 규칙의 기술서와 본보기. 오타면 가까운 이름을 준다 |
| `hanlint patterns --rule <규칙>` | 그 규칙을 피하는 문장 틀. 예시는 error 0 이 보장된다 |
| `hanlint rules` | 규칙 목록. 부류로 묶고 꺼진 것을 표시한다 |
| `hanlint baseline 글들/` | 지금 있는 지적을 잠근다. `--prune` 은 죽은 잠금을 치운다 |
| `hanlint 글들/ --baseline` | 잠근 것은 넘기고 새로 생긴 것만 막는다 |
| `hanlint 글.md --preset docs` | 설정 파일 없이 이번 검사의 글 종류만 정한다. 종류는 blog, report, docs, guide, essay, fiction, encyclopedia 이고 규칙 묶음과 견줄 프로파일이 따라온다 |
| `hanlint doctor` | 어느 설정을 읽었고 어느 분석기로 돌며 어느 규칙이 꺼져 있는지 |
| `hanlint init --preset docs` | 글의 종류에 맞춘 `hanlint.toml` |
| `hanlint 글.md --format compact --errors-only` | 한 줄에 지적 하나, error 만. 스크립트가 쓴다 |
| `hanlint 글.md --format json` | 본보기가 붙은 기계 판. `github` 은 GitHub Actions 주석 |
| `hanlint rules --format json` | 규칙 전부를 기술서와 본보기와 함께. 에이전트가 훑을 때 |
| `hanlint explain <규칙> --format json` | 규칙 하나의 기술서와 본보기와 틀을 한 덩어리로 |
| `hanlint - --path 초안.md` | stdin 으로 넣은 글을 그 이름으로 검사한다 |
| `hanlint audit 글.md` | 지문 지도와 분포. 색이 있는 자리가 구멍이다 |
| `hanlint map 글.md --format html` | 지도를 단일 HTML 로 |
| `hanlint print 글.md --layer sentences` | 문장, 문단, 절, 글의 지문을 JSON 으로 |
| `hanlint diff 전.md 후.md` | 두 초안의 짜임, 리듬, 지적 수의 변화 |
| `hanlint learn 전.md 후.md` | 사라진 문장 지적에서 사람이 승인할 프로젝트 본보기 후보 |
| `hanlint packet 글.md` | 초안, 대조 분포, 독자 상태, 고침 근거를 AI용 JSON으로 컴파일 |
| `hanlint profile build 글들/` | 참조 글의 분포 (프로파일). `--profile` 로 종류의 프로파일 대신 그것과 견준다 |
| `hanlint terms 글.md` | 한국어 학습용 어휘 C에만 등재된 화제어의 첫 자리를 찾는다. `--outside` 는 목록 밖 후보도 보인다 |
| `hanlint coverage review.json 글.md` | 사람 평가자의 지적 가운데 hanlint 가 같은 자리를 집은 비율 |

종료 코드는 지적이 없으면 0, error 가 있으면 1 이라 발행 게이트에 그대로 물린다. 두 구현은 같은 규칙, 같은
fixture, 같은 출력이다. 지문 지도와 프로파일과 감시와 학습 어휘 대조는 파이썬 쪽에만 있다.

## 규칙을 끄기

프리셋 위에서 더 끄려면 `hanlint.toml` 의 `disable` 에 이름을 넣는다. 한 자리에서만 끄려면 마크다운
주석을 쓴다. 상투어를 인용하는 문단처럼 규칙이 맞지만 그 자리만 예외일 때다.

```markdown
<!-- hanlint-disable cliche -->

AI 가 자주 쓰는 표현은 `핵심은`, `결국 중요한 것은` 처럼 눈에 띄는 것부터 지웁니다.

<!-- hanlint-enable cliche -->
```

`hanlint-disable-next` 는 다음 블록 하나만 끈다. 규칙 이름을 안 적으면 전부 끈다. 백틱과 따옴표 안은
인용이라 사전 규칙과 지시어 규칙이 처음부터 건너뛴다.

규칙이 아니라 글의 형식이 다르면 끄지 말고 설정으로 말한다. 강의 교안처럼 절 제목 아래에 문장형 부제를 두면
`headingSentenceMaxLevel = 2`, 장면 계약이나 도표 원문처럼 코드도 산문도 아닌 펜스가 있으면
`ignoreFences = ["course-scene", "mermaid"]` 다. 실측: 강의 여섯 편에 그냥 돌리면 error 89건이었고 이 둘을
적자 27건이 남았다. 남은 것은 전부 문장의 결함이었다.

## 파이썬에서

```python
from hanlint import lintText

for finding in lintText(text):
    print(finding.line, finding.rule, finding.why)
```

`lintFile`, `auditText`, `fingerprint` 도 같은 자리에 있다.

## CI 게이트로 물린다: pre-commit, GitHub Actions

pre-commit 훅과 GitHub Action 이 저장소 루트에 있다. 훅은 `.pre-commit-config.yaml` 에서 이 저장소를
가리키면 되고, 액션은 지적을 PR 의 줄 주석으로 단다. 쓰는 동안 계속 보려면 `hanlint watch 글.md` 가
저장할 때마다 다시 검사한다.

```yaml
- uses: eddmpython/hanlint@main
  with:
    files: docs/글.md
    errors-only: "true"
```

이미 문서가 쌓인 저장소면 `hanlint baseline docs/` 로 한 번 잠그고 `.hanlint-baseline.json` 을 커밋한다.
그러면 첫날부터 초록이고, 그 뒤로 누가 문장을 고치거나 새로 쓸 때만 막힌다.

## 무엇을 잡고 무엇은 안 잡나

경계는 [skills/specs/start/product.md](skills/specs/start/product.md) 에 있다. 안 잡는 것도 근거와 함께
적혀 있다. 뜻을 이해해야 잡히는 것, 취향, 그리고 만들었다가 실측에서 오탐이 이겨 뺀 규칙들이다.

규칙 하나는 파일 하나이고 자기 기술서를 docstring 으로 든다. 규칙마다 어떤 실제 글의 어떤 문장에서
왔는지가 거기 적혀 있다. 실측 없는 규칙은 넣지 않는다.

## 오탐 신고와 규칙 제안

정당한 문장이 잡혔거나 잡아야 할 자리를 놓쳤으면 이슈로 알려 주면 된다. 양식 두 개가 문장 원문과 근거를
묻는다. 오탐은 fixture 의 spare 로 박혀 다시는 잡히지 않게 되고, 제안은 실측 사례가 있어야 규칙이 된다.
절차는 [skills/specs/operation/feedback.md](skills/specs/operation/feedback.md) 에 있다.

## English

hanlint is a linter for Korean prose in Markdown. It reports only what can be decided by counting:
translationese, noun pile-ups, double passives, dangling demonstratives, fragmented paragraphs and
document-level structure. It does not judge whether writing is good, and it is not a spell checker.

Two implementations, zero runtime dependencies, identical output: `pip install hanlint` and
`npx hanlint`. Exit code is 1 when an error-level finding exists, so it drops into CI as a gate.
`hanlint baseline docs/` locks what already exists so an established repository starts green.

## 라이선스

MIT 다.
