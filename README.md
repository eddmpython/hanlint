# hanlint

한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는 린터다. 의존성이 없다.

글의 좋고 나쁨을 판정하지 않는다. 세어서 확정할 수 있는 결함만 집어서 자리와 이유를 돌려준다.
좋은 글인지는 사람과 LLM 평가자가 그 위에서 판단한다. hanlint 는 그 판단이 셈에 시간을 쓰지
않게 바닥을 깔아 주는 도구다.

## 설치

pip 하나면 된다. 형태소 분석기로 더 정밀하게 보려면 `hanlint[kiwi]` 를 따로 받는다. Node 쪽은 npm 에
같은 이름으로 있고 설치 없이 `npx hanlint 글.md` 로 바로 돈다.

```powershell
pip install hanlint
pip install hanlint[kiwi]
npx hanlint 글.md
```

두 구현은 같은 규칙, 같은 fixture, 같은 출력이다. 지문 지도와 프로파일과 kiwi 정밀 모드는 파이썬 쪽에만 있다.

## 사용

마크다운 파일 하나를 주면 된다.

```powershell
hanlint 글.md
```

지적마다 규칙 이름, 줄 번호, 인용 문장, 왜 문제인지가 붙는다. 기계가 고칠 수 있는 것은 고친
문장이 같이 온다. 종료 코드는 지적이 없으면 0, error 가 있으면 1 이라 발행 게이트에 그대로 물린다.

```text
글.md:12  [doublePassive]  결과가 저장되어집니다.
    되어지 는 이중 피동이다. 피동 하나로 줄인다
    고친 뒤: 결과가 저장됩니다.
```

다른 명령은 표에 있다.

| 명령 | 무엇 |
|---|---|
| `hanlint 글.md --format json` | 기계가 읽는 꼴. `github` 은 GitHub Actions 주석 |
| `hanlint audit 글.md` | 지문 지도와 분포. 색이 있는 자리가 구멍이다 |
| `hanlint map 글.md --format html` | 지도를 단일 HTML 로 |
| `hanlint print 글.md` | 문장, 문단, 절의 지문을 JSON 으로 |
| `hanlint rules` | 규칙 목록 |
| `hanlint explain <규칙>` | 규칙의 기술서. 왜, 어디서, 고치기, 안 잡는 것 |
| `hanlint init` | 주석 달린 `hanlint.toml` |
| `hanlint profile build 글들/` | 승인된 글의 문체 분포. `--profile` 로 새 글을 견준다 |

## 규칙을 끄기

글 전체에서 끄려면 `hanlint init` 이 만드는 `hanlint.toml` 의 `disable` 에 이름을 넣는다. 한 자리에서만
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

## AI 에게 시키기

`skills/use-hanlint/SKILL.md` 를 에이전트의 스킬 폴더에 두면 AI 가 글을 쓴 직후 스스로 검사하고
지적이 0 이 될 때까지 고친다.

## 무엇을 잡나

잡는 것과 잡지 않는 것은 [skills/specs/start/product.md](skills/specs/start/product.md) 에 있다.
규칙 하나는 파일 하나이고 자기 기술서를 docstring 으로 든다.

## 라이선스

MIT 다.
