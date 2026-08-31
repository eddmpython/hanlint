# hanlint

한국어 글에서 반복되는 결함을 결정적으로 잡는 린터다. 번역투, 상투어, 자주 틀리는 맞춤법과 띄어쓰기,
헷갈리는 말, 조각난 문단, 코드 튜토리얼의 계약 위반까지 집는다. 의존성이 없고 Node 18 이상이면 된다.

```powershell
npx hanlint
npx hanlint 글.md
npx hanlint fix 글.md
npx hanlint 글.md --format compact --errors-only
```

인자 없이 치면 첫 화면이 나온다. 이 폴더의 마크다운 이름으로 만든 예시와 지금 칠 수 있는 명령이 거기 있다.
파일 자리에 폴더를 주면 그 아래 마크다운을 전부 찾는다.

지적마다 규칙 이름, 줄 번호, 인용 문장, 왜 문제인지가 붙고 마지막 줄이 다음에 무엇을 하면 되는지 말한다.
고친 표기가 확정된 자리는 `fix` 가 원문에 적용한다. `--format json` 은 기계가 읽는 꼴이고 종료 코드는
지적이 없으면 0, error 가 있으면 1 이라 발행 게이트에 그대로 물린다. stdin 은 `npx hanlint - --path 이름.md`
로 받는다. 규칙 목록은 `npx hanlint rules`, 규칙의 기술서는 `npx hanlint explain <규칙>`, 지금 어느 설정으로
도는지는 `npx hanlint doctor` 다.

파이썬 판의 `hanlint learn 전.md 승인본.md --format toml`로 승인한 `[[patches]]`를 같은
`hanlint.toml`에 두면 npm 판도 같은 패치를 읽는다. 정규화한 원문, 규칙, 프리셋, 국소 표지, 독자 상태가
모두 같은 유일한 패치만 JSON 지적의 `patch`로 내고, 원문이 다르면 유사 문장이라도 기권한다.

같은 `learn` 출력에서 뜻과 적용 범위를 확인한 `[[operations]]`도 두 판이 함께 읽는다. 승인 조각이 현재
문장의 단어 경계 한 자리에만 있고 숫자, URL, 식별자, 경로, 코드, 링크 목적지가 그대로일 때 파일 JSON의
`operations[].operation.result`를 낸다. 한국어 고유명사와 프로젝트 용어는 `protectedTerms`에 적어 잠근다.
지시어와 의미 고침, 여러 자리 일치는 기권하며 원문 완전 일치 패치와 확정 fix가 먼저다.

글의 종류가 블로그가 아니면 프리셋을 먼저 고른다. `npx hanlint init --preset docs` 가 참고 문서에 맞지 않는
규칙을 끈 설정 파일을 만든다. `blog`, `report`, `docs`, `guide`, `essay`, `fiction`, `encyclopedia` 일곱이고
`npx hanlint rules` 가 지금 도는 목록을 낸다.

```js
import { lintFile } from "hanlint";

for (const finding of lintFile("글.md")) console.log(finding.line, finding.rule, finding.why);
```

파이썬 패키지 (`pip install hanlint`) 와 같은 규칙, 같은 fixture, 같은 출력이다. 지문 지도 (`audit`, `map`),
문체 프로파일, 초안 비교 (`diff`), 평가자 겹침 (`coverage`) 은 파이썬 쪽에만 있다. 무엇을 잡고 무엇을 잡지 않는지는
[저장소의 product 문서](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/product.md) 에 있다.

## 라이선스

코드와 나머지 데이터는 [MIT](LICENSE)다. `data/easyWords.json`은 국립국어원 자료의 파생물이며
[공공누리 제1유형 고지](koglType1.LICENSE.md)가 적용된다.
