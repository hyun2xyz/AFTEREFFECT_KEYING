# 처음 시작하기

이 폴더는 **Codex 또는 Claude Code와 함께** 그린스크린 촬영본을 키잉하고 After Effects에서
합성하는 수업용 starter입니다. Python·FFmpeg가 없는 컴퓨터도 설치 단계부터 시작할 수
있습니다. CorridorKey 2.0과 After Effects는 각 공식 출처에서 학생이 직접 준비하며,
이 폴더에 포함하지 않습니다.

## 포크해서 받기

공통강의의 Git 세팅(Git·GitHub CLI 설치와 `gh` 인증)을 마친 컴퓨터에서 시작합니다.
[포크로 시작하고 업데이트 받기](docs/fork-and-update.md) 1번의 문장으로 이 저장소를 내 GitHub
계정에 포크해서 받고, 받은 폴더를 Codex에서 다시 엽니다. 전역 스킬 설치는 필요하지 않습니다.

## 폴더를 연 뒤 이 문장을 붙여 넣기

> 이 폴더의 AGENTS.md와 .agents/skills/aftereffect-keying/SKILL.md를 읽고 시작해 주세요.
> 실제 OS와 GPU, 설치된 도구를 확인하고, OS setup 문서의 공식 출처로 빠진 것만 준비해 주세요.
> CorridorKey를 설치하기 전에 docs/rules.md 1장의 라이선스를 요약해 주세요.
> 제가 주는 짧은 그린스크린 영상을 docs/rules.md대로 한 단계씩 키잉하고, AE에서
> 배경을 바꾸는 과정까지 진행해 주세요. Adobe 로그인·결제·약관 동의와 드라이버 설치는
> 제가 직접 합니다. 원본은 보존하고, 확인한 범위와 남은 문제를 구분해 알려 주세요.
> 실패를 성공으로 보고하지 마세요.

## 진행 순서

1. 현재 OS의 [Windows setup](docs/setup-windows.md) 또는 [Mac setup](docs/setup-macos.md)만 읽습니다.
   NVIDIA RTX 30 시리즈 이상이 없으면 Keylight 경로로 진행합니다. Mac에서는 무료 CorridorKey가 실행되지 않으며,
   쓰려면 공식 유료판을 직접 구매해야 합니다(Mac setup 참고).
2. [workflow](docs/workflow.md)대로 내 영상과 `work/<shot>` 폴더를 정하고 `shot.json`을 적습니다.
3. 짧은 시험 키잉 → 전체 키잉 → 검수 → AE 합성 순서로 진행합니다. 각 단계의 규칙은
   [rules](docs/rules.md)에 있습니다.

첫 샷은 5–10초, 스크린 조명이 비교적 고르고 대상이 스크린 안에 들어오는 영상으로 시작합니다.

수업을 마치면 내 작업을 내 포크에 push하고, 강사가 업데이트를 알리면 upstream에서 pull합니다.
방법은 [포크로 시작하고 업데이트 받기](docs/fork-and-update.md)의 2·3번에 있습니다.
