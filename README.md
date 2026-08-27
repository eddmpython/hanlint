# hanlint

한국어 글에서 반복되는 결함을 결정적으로 잡는 린터이자 글쓴이의 글짓기 도구다. 의존성이 없다.

번역투와 상투어, 자주 틀리는 맞춤법과 띄어쓰기 (`됬`, `않 해`, `할수 있다`), 로서/로써 같은 헷갈리는 말,
지시어와 명사 쌓기, 조각난 문단, 도입과 결말의 개수 불일치, 앞에 나온 적 없는 기준값, 한 칸만 잣대가 다른
표, 글쓴이의 수정 이력, 그리고 코드 튜토리얼이라면 만들지 않은 파일을 읽는 자리와 설치 줄에 없는 import
까지 집는다. 항목마다 국립국어원 조항이나 실측 근거가 붙어 있고 고친 표기가 확정된 자리는 `hanlint fix`
가 바로 바꾼다.

글의 좋고 나쁨은 판정하지 않는다. 세어서 확정할 수 있는 결함만 집어서 자리와 이유를 돌려준다.
좋은 글인지는 사람과 LLM 평가자가 그 위에서 판단한다. hanlint 는 그 판단이 셈에 시간을 쓰지
않게 바닥을 깔아 주는 도구다.

## 30초 안에 첫 결과

설치는 pip 하나다. Node 만 있으면 설치 없이 `npx hanlint` 로 바로 돈다.

```powershell
pip install hanlint
hanlint
```

`hanlint` 를 인자 없이 치면 첫 화면이 나온다. 이 폴더에 있는 마크다운 이름으로 만든 예시 세 줄과 지금
칠 수 있는 명령이 거기 있다. 그다음에 그 파일 이름을 그대로 준다.

```powershell
hanlint 글.md
```

지적마다 규칙 이름, 줄 번호, 인용 문장, 왜 문제인지가 붙는다. 기계가 고칠 수 있는 것은 고친
문장이 같이 온다. 첫 줄은 어느 설정을 읽었는지고 마지막 줄은 다음에 무엇을 하면 되는지다. 종료 코드는
지적이 없으면 0, error 가 있으면 1 이라 발행 게이트에 그대로 물린다.

```text
설정: hanlint.toml

글.md:12  [doublePassive]
  결과가 저장되어집니다.
  되어지 는 이중 피동이다. 피동 하나로 줄인다
  고친 뒤: 결과가 저장됩니다.

다음: error 1건 가운데 1건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다
```

파일 자리에 폴더를 줘도 된다. 그 아래 마크다운을 전부 찾는다.

```powershell
hanlint blog/posts
```

형태소 분석기로 더 정밀하게 보려면 `pip install hanlint[kiwi]` 를 따로 받는다. 두 구현은 같은 규칙,
같은 fixture, 같은 출력이다. 지문 지도와 프로파일과 kiwi 정밀 모드는 파이썬 쪽에만 있다.

## 명령

| 명령 | 무엇 |
|---|---|
| `hanlint` | 첫 화면. 이 폴더의 파일 이름으로 만든 예시와 다음 걸음 |
| `hanlint 글.md` 또는 `hanlint 글들/` | 검사한다. 폴더면 그 아래 마크다운 전부 |
| `hanlint 글.md --format compact --errors-only` | 한 줄에 지적 하나, error 만. AI 와 스크립트가 쓴다 |
| `hanlint - --path 초안.md` | stdin 으로 넣은 글을 그 이름으로 검사한다 |
| `hanlint 글.md --format json` | 기계가 읽는 꼴. `github` 은 GitHub Actions 주석 |
| `hanlint fix 글.md` | 번역투, 명령형 뒤 마침표, 이중 부정처럼 확실한 자리를 고친다 |
| `hanlint doctor` | 어느 설정을 읽었고 어느 분석기로 돌며 어느 규칙이 꺼져 있는지 |
| `hanlint audit 글.md` | 지문 지도와 분포. 색이 있는 자리가 구멍이다 |
| `hanlint map 글.md --format html` | 지도를 단일 HTML 로 |
| `hanlint print 글.md --layer sentences` | 문장, 문단, 절, 글의 지문을 JSON 으로. 층 하나만 고를 수 있다 |
| `hanlint rules` | 규칙 목록. 부류로 묶고 꺼진 것을 표시한다 |
| `hanlint explain <규칙>` | 규칙의 기술서. 왜, 어디서, 고치기, 안 잡는 것. 오타면 가까운 이름을 준다 |
| `hanlint init --preset docs` | 글의 종류에 맞춘 `hanlint.toml`. 프리셋은 `blog`, `report`, `docs` |
| `hanlint profile build 글들/` | 승인된 글의 문체 분포. `--profile` 로 새 글을 견준다 |
| `hanlint diff 전.md 후.md` | 두 초안의 짜임, 리듬, 지적 수의 변화 |
| `hanlint coverage review.json 글.md` | 사람 평가자의 지적 가운데 hanlint 가 같은 자리를 집은 비율 |

백틱과 따옴표 안은 인용이라 사전 규칙과 지시어 규칙이 건너뛴다. 상투어를 인용하며 설명하는 글이 잡히지 않는다.

## 글의 종류를 먼저 고른다

기본은 블로그다. 독자를 부르고 절마다 눈에 보이는 결과를 남기는 글이 기준이라, 보고서나 참고 문서에
그대로 대면 맞지 않는 지적이 나온다. 그래서 프리셋이 있다.

```powershell
hanlint init --preset docs
```

`blog` 는 전부 켠다. `report` 는 독자 호출과 절 결과 요구를 끈다. `docs` 는 거기에 더해 검증 사실을
남기는 것과 그림을 `text` 펜스로 그리는 것을 끈다. 어느 규칙이 꺼졌는지는 `hanlint rules` 가 표시하고
`hanlint doctor` 가 한 줄로 답한다.

## 규칙을 끄기

프리셋 위에서 더 끄려면 `hanlint.toml` 의 `disable` 에 이름을 넣는다. 한 자리에서만
끄려면 마크다운 주석을 쓴다. 상투어를 인용하는 문단처럼 규칙이 맞지만 그 자리만 예외일 때다.

```markdown
<!-- hanlint-disable cliche -->

AI 가 자주 쓰는 표현은 `핵심은`, `결국 중요한 것은` 처럼 눈에 띄는 것부터 지웁니다.

<!-- hanlint-enable cliche -->
```

`hanlint-disable-next` 는 다음 블록 하나만 끈다. 규칙 이름을 안 적으면 전부 끈다.

## 파이썬에서

같은 일을 함수로 한다.

```python
from hanlint import lintText

for finding in lintText(text):
    print(finding.line, finding.rule, finding.why)
```

`lintFile`, `auditText`, `fingerprint` 도 같은 자리에 있다.

## 커밋과 PR 에서

pre-commit 훅과 GitHub Action 이 저장소 루트에 있다. 훅은 `.pre-commit-config.yaml` 에서 이 저장소를
가리키면 되고, 액션은 지적을 PR 의 줄 주석으로 단다. VS Code 확장 (`vscode/`) 은 저장할 때 검사해
밑줄로 보여 주고 확정된 자리는 quick fix 로 고친다.

```yaml
- uses: eddmpython/hanlint@main
  with:
    files: docs/글.md
    errors-only: "true"
```

## AI 에게 시키기

`skills/use-hanlint/SKILL.md` 를 에이전트의 스킬 폴더에 두면 AI 가 글을 쓴 직후 스스로 검사하고
지적이 0 이 될 때까지 고친다.

## 무엇을 잡나

잡는 것과 잡지 않는 것은 [skills/specs/start/product.md](skills/specs/start/product.md) 에 있다.
규칙 하나는 파일 하나이고 자기 기술서를 docstring 으로 든다.

## 오탐 신고와 규칙 제안

정당한 문장이 잡혔거나 잡아야 할 자리를 놓쳤으면 이슈로 알려 주면 된다. 양식 두 개 (오탐 신고,
규칙 제안) 가 문장 원문과 근거를 묻는다. 오탐은 fixture 의 spare 로 박혀 다시는 잡히지 않게 되고,
제안은 실측 사례가 있어야 규칙이 된다. 절차는
[skills/specs/operation/feedback.md](skills/specs/operation/feedback.md) 에 있다.

## 라이선스

MIT 다.
