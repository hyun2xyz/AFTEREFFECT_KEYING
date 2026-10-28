# After Effects 컴프 만들기

원본 플레이트와 결과 시퀀스를 레이어로 쌓은 **편집 가능한 AE 컴프**를 만듭니다.
`scripts/ae_comp.py`(Python 표준 라이브러리)가 샷 값으로 JSX를 만들고, 학생이 AE에서 실행합니다.
프리셋은 두 가지입니다. `keying`은 이미 뽑은 키 결과(CorridorKey 등)를 얹고, `keylight`는 AE의 Keylight로 직접
키를 뺍니다([5장](#5-keylight로-키-빼기keylight-프리셋)). 프리셋 이름을 생략하면 `keying`입니다.
AE MCP, 상시 브리지, 자동 저장·렌더는 쓰지 않습니다. 설정의 근거는 [rules](rules.md) 7장입니다.

## 만드는 컴프

| 레이어(위 → 아래) | 소스 | 해석 |
| --- | --- | --- |
| Key | `--key` (예: CorridorKey cutout 시퀀스, 필수) | 알파 Straight. 픽셀 종횡비 적용 |
| Background | `--background` 이미지 파일 또는 시퀀스 폴더(선택) | 알파 무시. 컴프 전체 길이 |
| Plate (reference) | `work/<shot>/frames/` (`--plate`) | **꺼 둔** 비교용 레이어. 컴프 크기·길이·FPS·픽셀 종횡비의 기준 |

16 bpc만 맞춥니다. 작업 색공간과 linear blending은 학생 프로젝트 설정을 그대로 둡니다. 단, **키가 EXR이면** 32 bpc,
sRGB IEC61966-2.1, linear blending으로 맞춥니다([6장](#6-corridorkey-최고-화질-알파exr-얹기)). 선형 작업이면 컷아웃의 색 공간을 프로젝트에 맞추고 이중 변환하지 않습니다([rules](rules.md) 7장).

- 픽셀 종횡비는 `--pixel-aspect 3/2` 또는 `shot.json`의 `"pixel_aspect": [3, 2]`로 줍니다.
  원본과 키 결과에 적용하고 배경 이미지에는 적용하지 않습니다. 없으면 AE가 파일에서 읽습니다.
- 접지 그림자·색 보정·가비지 마스크는 학생이 이 컴프 위에 따로 만듭니다.

스크립트는 **빈 프로젝트에서만** 폴더 하나(샷 이름), 푸티지, 컴프 하나를 추가합니다. 저장·닫기·렌더는
하지 않습니다. 중간에 실패하면 이번 실행에서 추가한 항목을 지우고 바꾼 프로젝트 설정을 되돌립니다.

## 1. 소스 확인

- 시퀀스는 **폴더 하나에 시퀀스 하나**입니다. 같은 이름, 같은 자릿수(0 채움), 빈 번호 없는 연속 번호여야
  합니다. 다른 파일이 섞여 있거나 번호가 빠지면 생성기가 멈춥니다(숨김 파일은 무시).
- 영상 파일은 받지 않습니다. FFmpeg로 PNG 시퀀스를 먼저 뽑습니다([workflow](workflow.md) 1단계).
- 결과 시퀀스는 원본과 같은 해상도여야 합니다. AE가 가져온 크기가 다르면 스크립트가 멈춥니다.
- FPS는 `--fps 30000/1001` 또는 `work/<shot>/shot.json`의 `"fps": [30000, 1001]`입니다.
- 샷 이름은 공백 없이 글자·숫자·`_`·`-`·`.`로 씁니다. 한글도 됩니다.

## 2. JSX 만들기(에이전트)

```sh
.venv/bin/python -B scripts/ae_comp.py keying --shot shot01 --key work/shot01/key/cutout --background work/shot01/background/street.jpg
```

```powershell
.\.venv\Scripts\python.exe -B scripts\ae_comp.py keying --shot shot01 --key work\shot01\key\cutout --background work\shot01\background\street.jpg
```

`work/<shot>/ae/build_comp.jsx`가 생기고, 레이어별 프레임 수와 `job` 번호가 출력됩니다.
옵션 전체는 `scripts/ae_comp.py keying --help`로 봅니다. 경로를 생략한 레이어는 위 표의 기본 폴더를 씁니다.
예전 명령(`scripts/ae_comp.py --shot … --key …`)도 그대로 `keying`으로 동작합니다.

## 3. AE에서 실행(학생)

1. 열려 있는 작업을 저장합니다. **File > New > New Project**로 빈 프로젝트를 엽니다.
2. **File > Scripts > Run Script File**에서 `work/<shot>/ae/build_comp.jsx`를 고릅니다.
3. 알림 없이 컴프가 Viewer에 열리고 `build_comp.result.json`이 생깁니다. 성공·실패는 이 결과 기록으로만 알립니다.
   AE가 이미 켜져 있으면 에이전트가 `scripts/keylight.py run <JSX>`로 같은 스크립트를 보낼 수도 있습니다.
4. **File > Save As**로 `work/<shot>/ae/<shot>.aep`에 직접 저장합니다.

## 4. 결과 확인(에이전트)

스크립트는 `work/<shot>/ae/build_comp.result.json`을 남깁니다. 다음을 확인합니다.

- `job_id`가 2단계에서 출력된 번호와 같은지(예전 기록을 읽지 않도록).
- `status`가 `ok`인지. 아니면 `error`를 학생에게 그대로 전합니다.
- `project`의 bpc·작업 색공간·linear blending, `comp`의 크기·픽셀 종횡비·프레임 수.
- `layers`(아래 → 위)의 `in_frame`·`out_frame`, 결과 레이어의 `alpha`가 `straight`인지.

그다음 학생과 함께 시작·중간·끝 프레임을 봅니다. 최종 파일은 마지막 프레임에 대상이 남아 있는지 확인합니다([rules](rules.md) 7장).

| 멈춘 이유 | 뜻 |
| --- | --- |
| 프로젝트에 이미 항목이 있음 | 아무것도 바꾸지 않았습니다. 새 프로젝트에서 다시 실행합니다 |
| `has no alpha channel` | 결과 시퀀스에 알파가 없습니다. RGBA로 다시 렌더합니다 |
| `imported as N frames` | AE가 읽은 프레임 수가 다릅니다. 폴더 내용을 확인합니다 |
| `is WxH, plate is WxH` | 결과 해상도가 원본과 다릅니다 |
| 색 관리가 OCIO(EXR 키일 때만) | Project Settings > Color를 Adobe로 둔 프로젝트에서 실행합니다 |
| 결과 기록을 쓰지 못함 | 이때만 AE에 알림 창이 뜹니다. AE 설정 Scripting & Expressions의 'Allow Scripts to Write Files and Access Network'가 꺼져 있으면 컴프는 만들어지고 기록만 빠집니다. 학생이 알림 내용을 알려 주거나 직접 켭니다. 에이전트가 이 설정을 바꾸지 않습니다 |

## 5. Keylight로 키 빼기(`keylight` 프리셋)

NVIDIA GPU가 없거나 Mac이면 AE의 Keylight 1.2로 키를 뺍니다. 슬라이더를 감으로 움직이지 않고, Keylight 공식 가이드의
순서(스크린 색 → Status·Screen Matte로 판단 → Clip Black/White → Clip Rollback/Softness → 가비지 → 번짐)를
**라운드**로 나눠 매번 스크립트·결과 기록·렌더한 확인 프레임·수치를 남깁니다. `plan`·`analyze`는 NumPy·OpenCV가 있는
`.venv` Python으로 실행합니다(`scripts/setup_environment.py --install`).

```sh
.venv/bin/python -B scripts/keylight.py plan --shot shot01
.venv/bin/python -B scripts/ae_comp.py keylight --shot shot01 --background work/shot01/background/street.jpg
.venv/bin/python -B scripts/keylight.py run work/shot01/ae/build_comp.jsx
.venv/bin/python -B scripts/keylight.py round --shot shot01 --set edge.clip_black=20 --set edge.clip_white=85
.venv/bin/python -B scripts/keylight.py run work/shot01/keylight/round_01/round.jsx
.venv/bin/python -B scripts/keylight.py analyze --shot shot01
```

Windows는 `.\.venv\Scripts\python.exe`로 실행하고, `run`에 `--afterfx "<AfterFX.exe 경로>"`를 줍니다(Windows의 `run`은
아직 실제로 확인하지 않았습니다). `run`을 쓰지 않으면 학생이 같은 JSX를 **File > Scripts > Run Script File**로 실행합니다.

1. **plan**: 원본에서 스크린 색(밝기 25–90% 구간 중앙값)과 녹색/파란색을 고르고, 모든 샘플 프레임에서 화면 가장자리에
   붙은 스크린이 아닌 영역(플래그·스탠드·레터박스)을 가비지 다각형으로 `shot.json`에 적습니다. 다각형은 스크린 안쪽으로
   높이의 약 1/72만큼 들어와 그림자 진 이음매가 아닌 깨끗한 스크린을 지납니다. `plan.png`의 자홍색 표시는 다각형이
   대상을 자르는 곳입니다. 대상이 아래 가장자리를 지나면 `--subject-touches bottom`을 줍니다.
2. **컴프**: Plate 레이어에 Keylight Core(꺼 둠)·Keylight Edge·Key Cleaner(꺼 둠)·Spill(Advanced Spill Suppressor,
   Ultra, 켜 둠)이 순서대로 들어가고, 셰이프 레이어 **Garbage Matte**가 Plate의 알파 트랙 매트가 됩니다. Keylight의
   Outside Mask는 쓰지 않습니다(마스크 경계를 따라 반투명한 선이 남았습니다). Screen Balance는 녹색 50, 파란색 95입니다.
3. **round**: 바꿀 값만 `--set 효과.항목=값`으로 줍니다. 효과는 `core`·`edge`·`cleaner`·`spill`, 켜고 끄기는
   `enabled=on|off`입니다. 스크립트는 그 값만 바꾸고 Status·Final·배경 합성·코어 매트를 프레임별로 렌더한 뒤 보기
   설정을 되돌립니다. 저장·닫기·렌더 큐는 쓰지 않습니다.
4. **analyze**: 수치는 Keylight가 아니라 **원본 플레이트**로 잽니다. 프레임마다 아래 네 값이 0.05% 이하면 통과입니다.

| 값 | 뜻 |
| --- | --- |
| `bg_leak` | 확실한 스크린(대상에서 떨어진 곳)인데 알파가 남은 비율 — 회색 막 |
| `garbage_leak` · `garbage_seam` | 가비지 다각형 밖, 다각형 바로 안쪽 띠에 알파가 남은 비율 |
| `core_holes` | 확실한 대상 안쪽인데 알파가 1이 아닌 비율 — 비치는 구멍 |

경계의 반투명 비율(soft edge)과 번짐(spill, 경계·안쪽이 아직 스크린 색으로 기운 비율)은 참고값입니다. 실제로 녹색인
대상도 번짐으로 잡히므로 `sheet.png`(원본 | Status | 체커 위 키 | 배경 합성 | 코어 | 확대)와 재생으로 판단합니다.

라운드 순서:

1. 기본값으로 한 번. 보통 스크린에 회색 막, 어두운 옷에 구멍이 생깁니다.
2. 한 패스: Status가 검게 유지될 때까지 `edge.clip_black`을 5씩 올리고, 안쪽이 채워질 때까지 `edge.clip_white`를
   5씩 내립니다(70 아래로 많이 내리지 않음). 장비·가장자리 누출은 Clip Black이 아니라 가비지로 뺍니다.
3. 안쪽을 채우려다 경계가 딱딱해지면(soft edge가 1라운드보다 크게 줄면) **멀티패스**: `--core on --set edge.clip_white=100`.
   코어 패스(Clip 30/60, Shrink −높이/240, View Intermediate Result)가 엣지 패스의 **Source Alpha = Add To Inside Mask**로
   들어가, 엣지 패스는 부드러운 경계를, 깎은 코어는 꽉 찬 안쪽을 맡습니다.
4. Spill은 켜 둔 채 번짐 값과 피부·흰 소품 색을 봅니다. Spill의 Key Color는 측정한 스크린 색이 아니라 **순수한 색상**
   (녹색 0,1,0 / 파란색 0,0,1)입니다. 측정한 색을 넣으면 일부만 억제됐습니다(연습 영상 경계 번짐: 끔 1.2–2.3%,
   측정한 색 0.6–1.5%, 순수 녹색 0%).
5. Key Cleaner는 재생에서 경계가 떨릴 때만 켭니다(경계를 무르게 만듭니다).

**AE 화면으로 확인**: 렌더한 확인 프레임이 근거이고, AE Viewer는 두 번째 확인입니다. Keylight Edge의 View를 Status나
Final Result로 바꾸고 시간을 옮겨 Viewer를 봅니다. Run Script File 같은 대화상자가 열려 있거나 AE 창이 다른
데스크톱에 있으면 Viewer가 다시 그려지지 않습니다(시간 표시만 바뀜). Status에서 검정은 알파 0, 흰색은 1, 회색은
반투명입니다. 스크린 위 회색 점은 누출, 대상 둘레의 얇은 회색 띠는 정상적인 부드러운 경계입니다.

## 6. CorridorKey 최고 화질 알파(EXR) 얹기

Windows(NVIDIA)에서 CorridorKey 2.0을 EXR로 출력하면 압축 영상 대신 프레임별 부동소수점 알파와 색을 그대로 AE에 얹을 수
있습니다. 설치와 `$Ck`·`$CkPython`은 [Windows setup의 CorridorKey 항목](setup-windows.md#4-corridorkey-20-공식-저장소에서-직접),
라이선스·옵션은 [rules](rules.md)에 있습니다.

```powershell
Push-Location $Ck
& $CkPython infer.py --input <원본_영상_또는_PNG_폴더> --output_dir <저장소>\work\shot01\key --outputs alpha cutout --output_format exr --exr_dtype float
Pop-Location
.\.venv\Scripts\python.exe -B scripts\ae_comp.py keying --shot shot01 --key work\shot01\key\<클립>_cutout_exr --background work\shot01\background\street.jpg
```

- `<클립>_cutout_exr/cutout_000000.exr`: straight(곱하지 않은) RGBA, 장면 선형(scene-linear) 색, 번짐 제거 포함,
  1을 넘는 밝은 값도 그대로입니다. 알파만 따로 필요하면 `<클립>_alpha_exr`을 씁니다. `--exr_dtype half`도
  VFX 표준이지만 "최고 화질"은 `float`입니다. 프레임당 용량이 커서 실행 전에 남은 공간을 확인합니다.
- `--cutout_linear`는 영상 출력에만 해당합니다. EXR 컷아웃은 항상 선형입니다.
- 키가 EXR이면 생성기가 프로젝트를 **32 bpc, 작업 색공간 sRGB IEC61966-2.1, linear blending**으로 맞춥니다. CorridorKey가
  선형 빛에서 합성하는 방식과 같습니다. OCIO 프로젝트에서는 멈춥니다.
- 확인 프레임 주의: 32 bpc 프로젝트에서 `saveFrameToPng`가 쓰는 16비트 PNG는 색 채널이 값의 1/10로 저장됩니다(알파는
  그대로, AE 26.5). 수치로 비교할 때 색에 10을 곱합니다.

## 검증 기록

2026-10-28, macOS, After Effects 26.3(26.3x87)에서 이 저장소의 `scripts/ae_comp.py`로 만든 JSX를
합성 시퀀스로 실행했습니다. 결과 기록은 [validation/ae-comp-macos-ae26.3-2026-10-28.json](validation/ae-comp-macos-ae26.3-2026-10-28.json)에 있습니다.
렌더 확인은 `saveFrameToPng`로 뽑은 8비트 PNG입니다.

| 확인 | 결과 |
| --- | --- |
| 프로젝트·컴프·레이어 읽기 | `16 bpc / None / linear off`, 1280×1080 PAR 1.5, 12프레임, 레이어 3개 |
| 키 영역(프레임 0·6·11) | 원본 키 색과 차이 0 |
| 배경(1920×1080 정사각 픽셀 → 1280×1080 PAR 3:2 컴프) | 99백분위 차이 1/255 |
| 알파 0 아래의 자홍 RGB / 꺼 둔 초록 원본 | 0 / 0픽셀 |
| 마지막 프레임(11)의 키 | 있음 |
| 한글 샷 이름·경로(`키잉_테스트`) | 가져오기·컴프 이름·결과 기록 정상 |

함께 확인한 것(세 저장소가 같은 `ae_comp.jsx`를 쓰며 REMOVE 설정으로 시험): 항목이 있는 프로젝트에서는 아무것도 바꾸지 않고 멈춤, 알파 없는 결과로 실패하면
추가 항목이 지워지고 8 bpc·작업 색공간 없음·linear 끔 설정으로 되돌아감, 이 과정에서 AE 경고 창이 뜨지 않음.
실패 후 작업 색공간을 `"None"`으로 되돌리면 AE가 `Profile "None" is missing` 경고 창을 띄워 스크립트가 멈추던
문제를 찾아, 빈 문자열로 해제하도록 고쳤습니다.

2026-10-29, macOS, After Effects 26.5(26.5x89)에서 `keylight` 프리셋과 EXR 키를 확인했습니다. 결과 기록은
[validation/keylight-macos-ae26.5-2026-10-29.json](validation/keylight-macos-ae26.5-2026-10-29.json),
[validation/keying-exr-macos-ae26.5-2026-10-29.json](validation/keying-exr-macos-ae26.5-2026-10-29.json)입니다.

| 확인 | 결과 |
| --- | --- |
| `keylight` 빌드(이 저장소 스크립트, Python 3.13·OpenCV 4.14 `.venv`) | `16 bpc`, 1280×720, 180프레임, Garbage Matte 알파 트랙 매트(꺼 둠), Core·Edge·Key Cleaner·Spill |
| 라운드(그린스크린 연습 영상, 어두운 옷; 이 저장소로 옮기기 전 같은 스크립트) | 기본값 실패(스크린 46%에 회색 막, 구멍 최대 4.8%) → 한 패스 `clip_black 20 / clip_white 85` 통과, soft edge 0.61–0.70 → 멀티패스 `clip_white 100` + 코어 통과, 구멍 0, soft edge 0.82–0.87, 번짐 0% |
| 이 저장소 스크립트로 최종 설정 한 라운드 | 같은 수치 재현(구멍 0, soft edge 0.82–0.87, 번짐 0%) |
| AE Viewer | 프레임 90 Status: 스크린 검정, 대상 흰색, 경계만 회색. Final Result: 녹색 테두리·막 없음 |
| EXR 키(CorridorKey 형식 합성 float 시퀀스 30프레임) | `32 bpc / sRGB IEC61966-2.1 / linear on`, 키 straight. 화면 값이 sRGB로 인코딩한 EXR과 0.0015 이내, 2.0 값 안 잘림, 알파 동일 |

아직 확인하지 않은 것: 실제 CorridorKey EXR 출력, Windows의 `keylight.py run --afterfx`, **Windows의 실제 AE**, 실제 학생 샷, 파일 쓰기 설정이 꺼진 AE, OCIO 프로젝트에서의
멈춤(읽기만 하는 검사), AE 26.3 이외 버전.
