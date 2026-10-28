# 키잉 규칙

그린·블루스크린 촬영본에서 인물·물체를 분리하고 After Effects에서 새 배경과 합성하는
규칙입니다. 기본 키어는 **CorridorKey 2.0** 오픈소스 Python판입니다(NVIDIA RTX 30 이상). 이 판은 Mac을 지원하지 않으므로
Mac에서는 **Keylight**가 기본이고, CorridorKey는 유료판을 산 경우에만 씁니다. 기준 사례는 공개 그린스크린 연습
영상 5개, 총 520프레임을 힌트 없이 처리한 테스트입니다(잔머리 80, 모션블러 50,
금속 안경 90, 연기 120, 조명이 고르지 않은 전신 180프레임). 잔머리, 모션블러의
반투명 경계, 렌즈·얇은 안경테, 연기, 얇은 천의 경계가 유지됐습니다. 연기·전신 샷에서는
촬영 장비가 남아 추가 마스크가 필요했습니다.

정답 매트가 없는 테스트이므로 이 결과는 "샘플 프레임을 눈으로 확인했고 배경 영역 알파가
0이었다"는 뜻이지, 어떤 영상이든 완벽하다는 뜻이 아닙니다.

## 1. 라이선스와 사용 범위 (먼저 읽기)

**CorridorKey 2.0**은 OSI 기준 오픈소스가 아니라, 코드와 가중치를 공개한 **Corridor Key Licence**
(CC BY-NC-SA 4.0을 변형하고 조건을 더한 라이선스)입니다. 공식 [README](https://github.com/nikopueringer/CorridorKey2.0)와
[LICENSE](https://github.com/nikopueringer/CorridorKey2.0/blob/master/LICENSE) 원문이 기준입니다.

| 할 수 있는 것 | 할 수 없는 것 |
| --- | --- |
| 상업 프로젝트 영상을 포함해 자유롭게 키잉에 사용 | 도구를 판매하거나, 코드·모델 접근에 요금을 받음 |
| 코드·모델을 고쳐 공개(무료 공개, 같은 라이선스, CorridorKey 이름 유지) | Corridor Digital 허가 없이 유료 API·추론 서비스로 제공 |
| 후원·원하는 만큼 내기(pay-what-you-want) 방식 배포 | 연 매출 2천만 달러 초과 조직이 좌석 구매 없이 사용 |

이 저장소의 규칙:
- 이 저장소에는 CorridorKey의 코드·가중치를 **넣지 않습니다**. 학생이 공식 저장소와
  공식 다운로드 스크립트로 직접 받습니다.
- 수업 자료·과제 결과 묶음에 CorridorKey 코드·가중치를 넣어 배포하거나, 유료로
  접근하게 하지 않습니다. 사용법을 가르치는 것과 도구를 파는 것은 다릅니다.
  애매하면 README에 적힌 contact@corridordigital.com으로 확인합니다.
- CorridorKey를 고친 버전을 공개하면 무료 공개, 같은 라이선스, CorridorKey 이름 유지를 지킵니다.

CorridorKey가 내려받는 **기반 모델 3개**는 각자의 라이선스를 따릅니다(이 저장소에도,
CorridorKey 저장소에도 포함되지 않음).

| 모델 | 출처 | 라이선스 |
| --- | --- | --- |
| C-RADIOv4-SO400M (NVIDIA) | https://huggingface.co/nvidia/C-RADIOv4-SO400M | NVIDIA Open Model License |
| MoGe-2 ViT-B (Microsoft) | https://github.com/microsoft/MoGe | MIT(코드·가중치) |
| RVM small (Google DeepMind) | https://github.com/google-deepmind/representations4d | 코드 Apache-2.0, 가중치 CC-BY 4.0 |

**연습 영상**: 기준 사례는 [Hollywood Camera Work 그린스크린 플레이트](https://www.hollywoodcamerawork.com/green-screen-plates.html)를
썼습니다. 로컬 연습은 허용되지만 **원본을 다시 올리거나 직접 다운로드 링크를 게시하지
않습니다**. 이 저장소도 출처 페이지만 링크합니다. 결과를 공개하기 전에 해당 페이지의
조건을 다시 확인합니다.

**배경 소스**: 출처와 라이선스가 분명한 것을 씁니다(예: [Poly Haven](https://polyhaven.com/license) CC0).

## 2. 도구 역할

| 단계 | 도구 | 역할 |
| --- | --- | --- |
| 키잉 | CorridorKey 2.0 (Python, NVIDIA RTX 30 이상) | 알파와 전경 색(despill 포함)을 추정 |
| 대체 키잉 | After Effects Keylight | NVIDIA GPU가 없거나(Mac 기본) 비교가 필요할 때. 측정 라운드·멀티패스 방법은 [ae-comp 5장](ae-comp.md#5-keylight로-키-빼기keylight-프리셋) |
| 검사 | FFmpeg·ffprobe, Python(NumPy·Pillow) | 프레임·FPS·픽셀 비율 확인, 알파 진단, 전체 디코드 |
| 합성 | After Effects | 원본 키 결과·배경·그림자를 분리한 편집 가능한 프로젝트 |

Mac이나 NVIDIA가 아닌 컴퓨터에서는 CorridorKey 오픈소스 Python판을 쓸 수 없습니다(공식 README는 NVIDIA CUDA GPU만
명시). 이때는 Keylight로 진행합니다. **Mac에서 CorridorKey를 쓰려면 공식 유료 앱·플러그인을 학생이 구매해야
합니다**([corridorkey.com](https://corridorkey.com), M 시리즈 Mac·macOS 14 이상, 2026-10-28 기준 베타, Intel Mac 미지원).
설치·활성화·출력 형식은 [Mac 준비](setup-macos.md#corridorkey-유료판mac)에 있습니다. 이 저장소에서는 유료판을 실행해
보지 않았습니다.

## 3. 소스 준비

- 가능하면 PNG·EXR 이미지 시퀀스로 작업합니다. 압축 영상이면 원본을 그대로 두고
  작업 프레임을 뽑습니다.
- FPS, 저장 해상도, **픽셀 종횡비(PAR)**를 기록합니다. 기준 사례 일부는 1280×1080에
  PAR 3:2로 저장돼 화면에서는 1920×1080으로 보여야 했습니다. 키잉 전에 리사이즈하지
  않습니다(CorridorKey는 원본 해상도를 유지합니다).
- 색 공간을 확인합니다. 일반 영상·PNG는 디스플레이 코딩으로 처리하고, 선형 EXR이면
  `--frame_dir_linear`를 씁니다.

## 4. 첫 실행: 힌트 없이 짧게

- 먼저 짧은 구간으로 시험합니다(`--num_frames`, `--start_mode middle`).
- 기준 사례 설정: 힌트 없음, 자동 VRAM, `--despill_strength 0.5`(기본값),
  `--outputs alpha fg checker cutout`.
- 메모리는 자동으로 잡힙니다. 메모리 부족 오류가 나면 `--low_vram`과 더 작은
  `--hann_chunk`를 씁니다(시간적 일관성이 조금 줄어듭니다).
- 처리 속도 참고(RTX 4070 Ti SUPER 16GB): 1280×1080 약 1 fps, 960×720 약 2.7 fps,
  최대 메모리 예약 약 12 GiB. 긴 영상은 백그라운드로 실행합니다.

## 5. 결과가 틀릴 때

- 엉뚱한 대상을 고르면 첫 프레임 매트를 힌트로 줍니다(`--hint_first_frame`, 흰색이 대상,
  검은색이 배경, `--hint_quality 0.95`). 필요하면 전체 힌트 영상(`--hint_video`)을 씁니다.
- 스탠드·조명 장비·스크린 밖 영역은 AE에서 **가비지 마스크**로 뺍니다. 키어 설정을
  세게 올려 장비를 지우려 하지 않습니다(경계가 상합니다).
- 녹색 번짐이 남으면 despill 강도를 조정하고, 경계 색은 합성 단계에서 맞춥니다.

## 6. 검수

- 검정·흰색·체커 배경 위에서 처음·중간·끝과 동작이 큰 프레임을 확대해 봅니다.
  잔머리, 모션블러, 투명·반투명(유리·연기·천) 경계를 따로 봅니다.
- 배경만 보이는 영역의 알파 평균·최댓값(0이어야 함)과, 확실한 대상 영역의 알파
  (1에 가까워야 함)를 전체 프레임에서 잽니다. 정답 매트가 없으면 이 값은 정확도
  점수가 아니라 진단값이라고 적습니다.
- 재생해서 경계의 깜빡임을 봅니다. 몇 프레임 샘플 확인으로 깜빡임이 없다고 하지 않습니다.
- 모든 출력 파일을 전체 디코드하고 프레임 수·FPS를 원본과 맞춥니다.

## 7. After Effects 합성

- 새 프로젝트로 만들고, Python이 만든 JSX를 학생이 **File → Scripts → Run Script File**로
  실행하거나 학생이 직접 가져옵니다. 열려 있는 작업을 덮어쓰지 않습니다.
- 알파가 있는 출력(EXR 또는 ProRes 4444)을 가져와 **Interpret Footage**에서 알파를
  Straight로, 픽셀 종횡비와 FPS를 원본에 맞춥니다.
- 최고 화질은 EXR입니다: `--outputs alpha cutout --output_format exr --exr_dtype float`. 컷아웃 폴더를
  `scripts/ae_comp.py keying --key`에 주면 32 bpc·sRGB IEC61966-2.1·linear blending 프로젝트로 맞춥니다
  ([ae-comp 6장](ae-comp.md#6-corridorkey-최고-화질-알파exr-얹기)). EXR 컷아웃은 항상 선형입니다.
- 영상(ProRes 4444) 컷아웃을 선형 작업(16·32 bpc, linear blending)에 쓰면 `--cutout_linear`로 선형 컷아웃을 받거나,
  기본 sRGB 컷아웃의 색 공간을 프로젝트에 맞게 해석합니다. 이중 변환하지 않습니다.
- 배경은 원근·카메라 높이·빛 방향이 맞는 것을 고릅니다. 키 결과, 배경, 접지 그림자,
  색 보정을 각각 편집 가능한 레이어로 둡니다.
- 전경과 배경의 색·노출·블러·그레인을 맞춥니다. 발이 보이면 접지 그림자를 따로 만듭니다.
- 최종 MP4를 전체 디코드하고 **마지막 프레임**에 대상이 남아 있는지 확인합니다(소스
  마지막 프레임 길이가 0이면 인물이 사라지는 문제가 있었습니다). 색 태그(BT.709)를 확인합니다.

## 8. 보고

샘플 프레임 확인 범위, 알파 진단값, 남은 문제(장비 잔여, 깜빡임, 경계 색)를 따로 적습니다.
화면에서 설득력이 없으면 기술 검수를 통과해도 실패로 판단합니다.
