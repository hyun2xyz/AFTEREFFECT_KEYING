# Mac 준비

CorridorKey 2.0의 **무료 오픈소스 Python판은 MacBook·iMac 등 Mac에서 실행되지 않습니다.** 공식
[README](https://github.com/nikopueringer/CorridorKey2.0)가 요구하는 것은 NVIDIA GPU(RTX 30 이상)와 CUDA이고, Mac 지원은
적혀 있지 않습니다. 에이전트도 Mac에서는 이 판을 설치하거나 가중치(약 5 GB)를 받지 않습니다.
Mac에서는 두 가지 중 하나로 진행합니다.

1. After Effects에 함께 설치되는 **Keylight**로 키잉합니다(추가 구매 없음. 이 저장소의 규칙 3장, 6–8장은 그대로 적용).
2. Mac에서 CorridorKey를 쓰려면 Corridor Digital의 **공식 유료 앱·플러그인**([corridorkey.com](https://corridorkey.com))을
   학생이 직접 구매합니다(아래 "CorridorKey 유료판").

## CorridorKey 유료판(Mac)

| 항목 | 공식 안내(2026-10-28 확인) |
| --- | --- |
| 지원 Mac | M 시리즈 칩, macOS 14 이상. **Intel Mac은 지원하지 않습니다** |
| 상태 | 베타. 가격·판매 시작·정식 출시 일정은 공식 페이지에서 확인합니다 |
| Mac에서 쓰는 곳 | 단독 앱, DaVinci Resolve·Nuke(OpenFX 플러그인), Blender 애드온. 판매 페이지는 2.0.0.146부터 After Effects·Premiere Pro 플러그인도 Mac에 포함된다고 안내합니다(설명서에는 아직 없으므로 설치 후 AE 효과 목록에서 확인) |
| 설치·활성화 | [Download](https://corridorkey.com/download/) 페이지의 macOS 설치 파일. 처음 실행할 때 활성화 키를 **학생이 직접** 입력합니다 |
| 라이선스 | 유료판 약관을 따릅니다. 규칙 1장의 오픈소스판 Corridor Key Licence와 다릅니다 |

순서:

1. Mac의 칩이 M 시리즈인지 확인합니다(Apple 메뉴 > 이 Mac에 관하여). Intel이면 Keylight로 진행합니다.
2. 구매·설치·활성화는 학생이 합니다. 에이전트는 결제하거나 활성화 키를 입력하지 않습니다.
3. 짧은 구간(24프레임 정도)으로 먼저 키를 뽑고, 검정·흰색·체커 위에서 Keylight 결과와 비교합니다.
4. 단독 앱의 Output은 Premultiplied(미리 곱한 RGB+알파), Matte(알파만), Straight FG(곱하지 않은 전경 색), Original입니다.
   [AE 컴프 생성기](ae-comp.md)는 **straight 알파 RGBA** 시퀀스를 받으므로 Premultiplied 출력을 그대로 넣지 않습니다
   (가장자리가 어두워짐). Straight FG와 Matte를 같은 번호끼리 합쳐 straight RGBA로 만들거나, AE 플러그인을 쓰면 AE
   안에서 원본 레이어에 효과로 적용합니다.

유료판은 이 저장소에서 실제로 실행해 보지 않았습니다. 위 표는 공식 페이지와
[설명서](https://help.corridorkey.com/docs/manual/)를 옮긴 것이며, 바뀔 수 있으니 설치 전에 공식 페이지를 다시 확인합니다.

## 시작

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
`.venv`에는 검사용 NumPy·Pillow와 Keylight 측정(`scripts/keylight.py`)용 OpenCV만 설치합니다.

## 2. After Effects와 연습 영상

[Adobe 공식 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)를
따라 학생 자신의 계정·라이선스로 설치합니다.

연습 영상은 [Hollywood Camera Work 그린스크린 플레이트](https://www.hollywoodcamerawork.com/green-screen-plates.html)
페이지에서 학생이 직접 받습니다. 로컬 연습용이며, 원본을 다시 올리거나 직접 다운로드
링크를 게시하지 않습니다.
