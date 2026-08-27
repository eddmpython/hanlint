# hanlint

한국어 글에서 반복되는 결함을 결정적으로 잡는 린터다. 번역투, 상투어, 자주 틀리는 맞춤법과 띄어쓰기,
헷갈리는 말, 조각난 문단, 코드 튜토리얼의 계약 위반까지 집는다. 의존성이 없고 Node 18 이상이면 된다.

```powershell
npx hanlint 글.md
npx hanlint fix 글.md
npx hanlint 글.md --format compact --errors-only
```

지적마다 규칙 이름, 줄 번호, 인용 문장, 왜 문제인지가 붙는다. 고친 표기가 확정된 자리는 `fix` 가 원문에
적용한다. `--format json` 은 기계가 읽는 꼴이고 종료 코드는 지적이 없으면 0, error 가 있으면 1 이라 발행
게이트에 그대로 물린다. stdin 은 `npx hanlint - --path 이름.md` 로 받는다. 규칙 목록은 `npx hanlint rules`,
규칙의 기술서는 `npx hanlint explain <규칙>` 이다.

```js
import { lintFile } from "hanlint";

for (const finding of lintFile("글.md")) console.log(finding.line, finding.rule, finding.why);
```

파이썬 패키지 (`pip install hanlint`) 와 같은 규칙, 같은 fixture, 같은 출력이다. 지문 지도 (`audit`, `map`),
문체 프로파일, 초안 비교 (`diff`), 평가자 겹침 (`coverage`), 형태소 정밀 모드 (kiwi) 는 파이썬 쪽에만 있다. 무엇을 잡고 무엇을 잡지 않는지는
[저장소의 product 문서](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/product.md) 에 있다.

MIT.
