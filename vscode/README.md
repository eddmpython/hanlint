# hanlint (VS Code)

한국어 마크다운을 열고 저장할 때 hanlint 로 검사해 지적을 밑줄로 보여 준다. 번역투와 명령형 뒤 마침표처럼
고친 표기가 확정된 자리는 전구 메뉴의 quick fix 로 바로 바꾼다.

기본 실행 명령은 `npx --yes hanlint` 라 Node 만 있으면 된다. 다른 실행을 쓰려면 설정 `hanlint.command` 에
적는다 (예: `node C:/repo/hanlint/npm/bin/hanlint.js`). notice 를 숨기려면 `hanlint.errorsOnly` 를 켠다.

규칙이 왜 있는지는 터미널에서 `npx hanlint explain <규칙>` 이 답한다. MIT.
