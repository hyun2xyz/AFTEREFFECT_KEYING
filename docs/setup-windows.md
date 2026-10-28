# Windows 준비

Windows 10/11 x64와 **NVIDIA RTX 30 시리즈 이상** GPU 기준입니다(CorridorKey 공식 조건:
1440p까지 VRAM 4 GB, 4K는 6 GB). NVIDIA GPU가 없으면 4장의 CorridorKey를 건너뛰고
After Effects Keylight로 진행합니다. [START-HERE](../START-HERE.md)대로 포크해서 받은 저장소 폴더를
에이전트와 PowerShell의 작업 폴더로 선택합니다.

```powershell
py -3.12 -B scripts/setup_environment.py --check
```

빠진 항목이 있으면 종료 코드 `1`과 이유를 출력하고 아무것도 바꾸지 않습니다.
`nvidia_smi`가 GPU 이름을 보여 주면 드라이버가 설치된 상태입니다.

## 1. Python, Git, NVIDIA 드라이버

- Python **3.12 / 3.13**: [Python 공식 Windows 설치기](https://www.python.org/downloads/windows/) 또는
  `winget install --id Python.Python.3.12 --exact --source winget --scope user --architecture x64`.
  기준 사례는 3.12.10에서 CorridorKey를 실행했습니다.
- Git: CorridorKey 의존성 하나가 Git 저장소에서 설치됩니다.
  [Git 공식 Windows 다운로드](https://git-scm.com/downloads/win) 또는
  `winget install --id Git.Git --exact --source winget`.
- NVIDIA 드라이버: [NVIDIA 공식 드라이버](https://www.nvidia.com/en-us/drivers/)에서 최신 드라이버를
  설치합니다. 드라이버 설치·재부팅은 학생이 직접 합니다.

## 2. FFmpeg

[FFmpeg 공식 Windows 링크](https://ffmpeg.org/download.html#build-windows)가 연결하는
[Gyan release essentials ZIP](https://www.gyan.dev/ffmpeg/builds/)을 받습니다. CorridorKey도
`ffmpeg`를 사용합니다.

```powershell
$ToolRoot = Join-Path $env:LOCALAPPDATA 'AFTEREFFECT_KEYING'
New-Item -ItemType Directory -Path (Join-Path $ToolRoot 'tools') -Force | Out-Null
$Zip = Join-Path $ToolRoot 'tools\ffmpeg-release-essentials.zip'
Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $Zip
Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256' -OutFile "$Zip.sha256"
$Expected = [regex]::Match((Get-Content "$Zip.sha256" -Raw), '\b[a-fA-F0-9]{64}\b').Value
if (-not $Expected -or (Get-FileHash $Zip -Algorithm SHA256).Hash -ne $Expected) { throw 'FFmpeg SHA256 mismatch' }
Expand-Archive -Path $Zip -DestinationPath (Join-Path $ToolRoot 'tools\FFmpeg')
$Ffmpeg = (Get-ChildItem (Join-Path $ToolRoot 'tools\FFmpeg') -Filter ffmpeg.exe -Recurse | Select-Object -First 1).FullName
$Ffprobe = Join-Path (Split-Path $Ffmpeg) 'ffprobe.exe'
```

## 3. 이 저장소의 설정과 검사 패키지

```powershell
py -3.12 -B scripts/setup_environment.py --configure --ffmpeg $Ffmpeg --ffprobe $Ffprobe
py -3.12 -B scripts/setup_environment.py --install
```

`.venv`에는 검사용 NumPy·Pillow와 Keylight 측정(`scripts/keylight.py`)용 OpenCV만 설치합니다. CorridorKey는 아래처럼 **별도 폴더와
별도 환경**에 설치합니다(PyTorch CUDA 버전이 섞이지 않게).

## 4. CorridorKey 2.0 (공식 저장소에서 직접)

먼저 [docs/rules.md의 라이선스](rules.md#1-라이선스와-사용-범위-먼저-읽기)를 읽습니다.
코드와 가중치는 이 저장소에 포함하지 않으며, 공식 출처에서 받습니다.
기준 사례는 commit `485f5e9ab759ead6138cc990776184b59d6ea971`에서 확인했습니다.

```powershell
$Ck = Join-Path $ToolRoot 'CorridorKey2.0'
git clone https://github.com/nikopueringer/CorridorKey2.0.git $Ck
git -C $Ck checkout 485f5e9ab759ead6138cc990776184b59d6ea971
py -3.12 -m venv (Join-Path $Ck 'venv')
$CkPython = Join-Path $Ck 'venv\Scripts\python.exe'
& $CkPython -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128
& $CkPython -m pip install -r (Join-Path $Ck 'requirements.txt')
Push-Location $Ck; & $CkPython scripts/download_weights.py; Pop-Location
py -3.12 -B scripts/setup_environment.py --configure --corridorkey (Join-Path $Ck 'infer.py')
```

- PyTorch 버전과 CUDA 인덱스는 [CorridorKey README](https://github.com/nikopueringer/CorridorKey2.0)의
  테스트 버전입니다. 다른 버전을 쓰면 README와 [PyTorch 공식 안내](https://pytorch.org/get-started/locally/)를 확인합니다.
- `download_weights.py`는 약 5 GB를 받습니다. CorridorKey 가중치는
  [Hugging Face](https://huggingface.co/nikopueringer/CorridorKey2.0)에서, 기반 모델 3개(C-RADIOv4,
  MoGe-2, RVM)는 각 원 배포처에서 고정 리비전으로 받습니다. 각 라이선스는 rules 1장에 있습니다.
- 받은 코드·가중치·`venv`를 이 저장소나 과제 결과에 복사하지 않습니다.

설치 확인은 짧은 구간 실행으로 합니다(규칙 4장).

```powershell
Push-Location $Ck
& $CkPython infer.py --input <짧은_영상_또는_프레임_폴더> --output_dir <work\shot\key> --num_frames 24 --start_mode middle
Pop-Location
```

AE에 얹을 최고 화질 알파는 EXR로 받습니다: `--outputs alpha cutout --output_format exr --exr_dtype float`.
컷아웃 폴더를 `scripts/ae_comp.py keying --key`에 주면 32 bpc 선형 프로젝트로 맞춥니다([ae-comp 6장](ae-comp.md#6-corridorkey-최고-화질-알파exr-얹기)).

## 5. After Effects와 연습 영상

[Adobe 공식 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)를
따라 학생 자신의 계정·라이선스로 설치합니다. Keylight는 AE에 함께 설치됩니다.

연습 영상은 [Hollywood Camera Work 그린스크린 플레이트](https://www.hollywoodcamerawork.com/green-screen-plates.html)
페이지에서 학생이 직접 받습니다. 로컬 연습용이며, 원본을 다시 올리거나 직접 다운로드
링크를 게시하지 않습니다.
