# AFTEREFFECT_KEYING

**VFX 학생이 LLM 에이전트와 함께 시작하는 키잉 스킬의 출발점.**
그린·블루스크린 촬영본을 CorridorKey 2.0(또는 After Effects Keylight)으로 키잉하고,
알파를 검수한 뒤 After Effects에서 새 배경과 합성합니다. AE MCP나 별도 서버는 쓰지 않습니다.

> **라이선스 먼저.** CorridorKey 2.0은 상업 영상 키잉에 쓸 수 있지만, 도구 판매·유료
> 서비스 제공이 금지된 Corridor Key Licence(CC BY-NC-SA 4.0 변형)입니다. 이 저장소는
> CorridorKey 코드·가중치를 포함하지 않고, 학생이 공식 저장소에서 직접 받게 합니다.
> 자세한 내용은 [rules 1장](docs/rules.md#1-라이선스와-사용-범위-먼저-읽기)에 있습니다.

## 학생은 이렇게 시작합니다

공통강의의 Git 세팅을 마친 컴퓨터에서, 이 저장소를 내 GitHub 계정에 **포크**해서 시작합니다.

1. Codex 또는 Claude Code에 붙여 넣습니다.

   > https://github.com/hyun2xyz/AFTEREFFECT_KEYING 를 제 GitHub 계정으로 포크해서 문서(Documents) 폴더에
   > 받아 주세요. 끝나면 origin과 upstream 주소를 보여 주세요.

2. 받은 `AFTEREFFECT_KEYING` 폴더를 Codex에서 다시 열고 [START-HERE.md](START-HERE.md)의 문장이나
   다음처럼 요청합니다.

> START-HERE.md, AGENTS.md와 공유 스킬을 읽고 제 컴퓨터와 GPU부터 확인해 주세요.
> CorridorKey 라이선스를 먼저 요약해 주고, 필요한 것만 공식 출처에서 설치 안내해 주세요.
> 제가 주는 짧은 그린스크린 영상을 키잉하고 AE에서 배경을 바꾸는 과정을 한 단계씩
> 진행해 주세요. 원본은 보존하고, 확인한 범위와 남은 문제를 구분해 알려 주세요.

- [포크로 시작하고 업데이트 받기](docs/fork-and-update.md)
- [Windows 준비(NVIDIA)](docs/setup-windows.md)
- [Mac 준비(Keylight, 또는 CorridorKey 유료판 구매)](docs/setup-macos.md)
- [키잉 규칙과 라이선스](docs/rules.md)
- [첫 영상부터 AE까지](docs/workflow.md)
- [AE 컴프 만들기](docs/ae-comp.md)

## 첫 버전의 범위

1. 촬영본의 FPS·저장 해상도·픽셀 종횡비를 기록하고, 리사이즈 없이 작업 프레임을 준비합니다.
2. CorridorKey 2.0을 힌트 없이 짧게 시험하고, 필요하면 첫 프레임 힌트로 다시 실행합니다.
3. 검정·흰색·체커 위 확대 확인, 배경·대상 영역 알파 진단, 재생으로 깜빡임을 봅니다.
4. 장비는 가비지 마스크로 빼고, AE에서 배경·접지 그림자·색을 맞춰 합성합니다.

이 범위는 공개 그린스크린 연습 영상 5개(잔머리, 모션블러, 금속 안경, 연기, 조명이
고르지 않은 전신), 총 520프레임을 CorridorKey 2.0으로 처리한 테스트를 바탕으로 정했습니다.
정답 매트가 없는 테스트이며, 어떤 촬영본이든 완벽하다는 뜻은 아닙니다.

## 에이전트/개발자

공유 스킬은 [.agents/skills/aftereffect-keying/SKILL.md](.agents/skills/aftereffect-keying/SKILL.md)입니다.
Codex는 저장소 스킬을 쓰고, Claude Code는 `CLAUDE.md`에서 같은 지침을 읽습니다.

```powershell
py -3.12 -B scripts/setup_environment.py --check
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

`scripts/`에는 설치 점검 도구, AE 컴프 JSX 생성기(`ae_comp.py`), AE Keylight 측정 라운드 도구(`keylight.py`)가 있습니다
([사용법](docs/ae-comp.md): Keylight 멀티패스 5장, CorridorKey EXR을 AE에 얹기 6장).
실행 래퍼·알파 진단은 에이전트가 샷마다 `work/<shot>/`에 만들고, 실제 샷에서 통과한 것만 `scripts/`로 옮깁니다.
[출처·라이선스](THIRD_PARTY_NOTICES.md)를 확인하세요.
