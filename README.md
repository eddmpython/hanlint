# hanlint

한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는 린터다.

글의 좋고 나쁨을 판정하지 않는다. 세어서 확정할 수 있는 결함만 집어서 자리와 이유를 돌려준다.
좋은 글인지는 사람과 LLM 평가자가 그 위에서 판단한다. hanlint 는 그 판단이 셈에 시간을 쓰지
않게 바닥을 깔아 주는 도구다.

## 설치

```powershell
pip install hanlint
```

## 사용

```powershell
hanlint 글.md
```

지적마다 규칙 이름, 줄 번호, 인용 문장, 왜 문제인지가 붙는다. `--json` 을 붙이면 기계가 읽는
꼴로 나온다. 규칙 목록은 `hanlint --list-rules` 다.

무엇을 잡고 무엇을 잡지 않는지는 [skills/specs/start/product.md](skills/specs/start/product.md) 에 있다.
