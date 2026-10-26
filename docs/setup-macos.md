# Mac 준비

CorridorKey 2.0의 공개 Python판은 **NVIDIA GPU(CUDA)**가 필요해서 Mac에서는 동작하지
않습니다. Mac에서는 두 가지 중 하나로 진행합니다.

1. After Effects에 함께 설치되는 **Keylight**로 키잉합니다(이 저장소의 규칙 3장, 6–8장은 그대로 적용).
2. 학생이 선택해 Apple Silicon을 지원하는 공식 유료 플러그인·앱([corridorkey.com](https://corridorkey.com))을
   씁니다. 구매·약관 동의는 학생이 직접 하며, 공개 Python판과 설치 방법이 다릅니다.

[START-HERE](../START-HERE.md)대로 포크해서 받은 저장소 폴더를 에이전트에 엽니다.

```sh
python3.13 -B scripts/setup_environment.py --check
```

## 1. Python과 FFmpeg

[Homebrew 공식 설치 안내](https://brew.sh/)를 확인하고
[Python 3.13](https://formulae.brew.sh/formula/python@3.13)과
[FFmpeg](https://formulae.brew.sh/formula/ffmpeg)을 설치합니다.
Homebrew는 공통강의 Git 세팅에서 설치했습니다. 없다면 아래 공식 설치 명령은 **학생이 터미널 앱에서
직접** 실행합니다. 관리자 암호를 입력해야 해서 에이전트가 대신 끝낼 수 없습니다.

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

```sh
TASK_BREW="$(command -v brew 2>/dev/null || true)"
[ -x "$TASK_BREW" ] || TASK_BREW=/opt/homebrew/bin/brew
[ -x "$TASK_BREW" ] || TASK_BREW=/usr/local/bin/brew
"$TASK_BREW" install python@3.13 ffmpeg
TASK_PYTHON="$("$TASK_BREW" --prefix python@3.13)/bin/python3.13"
"$TASK_PYTHON" -B scripts/setup_environment.py --configure
"$TASK_PYTHON" -B scripts/setup_environment.py --install
.venv/bin/python -B scripts/setup_environment.py --check
```

`nvidia_smi`가 없다는 표시는 Mac에서 정상이며 검사 실패가 아닙니다.
`.venv`에는 검사용 NumPy·Pillow만 설치합니다.

## 2. After Effects와 연습 영상

[Adobe 공식 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)를
따라 학생 자신의 계정·라이선스로 설치합니다.

연습 영상은 [Hollywood Camera Work 그린스크린 플레이트](https://www.hollywoodcamerawork.com/green-screen-plates.html)
페이지에서 학생이 직접 받습니다. 로컬 연습용이며, 원본을 다시 올리거나 직접 다운로드
링크를 게시하지 않습니다.
