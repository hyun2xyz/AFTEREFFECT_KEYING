# 첫 영상부터 After Effects까지

한 번에 한 단계씩 진행합니다. 각 단계가 끝나면 `work/<shot>/next.md`에 만든 파일,
확인한 것, 남은 문제, 다음 단계 하나를 적습니다. 규칙의 근거는 [rules](rules.md)에 있습니다.

## 작업 폴더

```text
work/<shot>/
  source/        원본 링크 또는 복사본(원본은 수정하지 않음)
  frames/        작업 프레임(PNG·EXR)
  shot.json      FPS, 저장 해상도, 픽셀 종횡비, 색 공간, 구간
  key/           CorridorKey 출력(alpha, fg, checker, cutout), processing.log
  masks/         첫 프레임 힌트, 가비지 마스크
  background/    배경 소스와 출처·라이선스 메모
  ae/            생성한 JSX, 저장한 AEP
  review/        검정·흰색·체커 비교, 알파 진단 report.json
  next.md
```

`work/`는 Git에 올리지 않습니다. 연습 영상·결과·AEP는 각자의 컴퓨터에만 둡니다.

## 1. 샷 준비

ffprobe로 FPS·저장 해상도·픽셀 종횡비를 읽어 `shot.json`에 적습니다. 영상이면 원본을
그대로 두고 작업 프레임을 뽑습니다. 리사이즈하지 않습니다.

## 2. 짧은 시험 키잉

CorridorKey를 힌트 없이 24프레임 정도로 먼저 실행합니다. NVIDIA GPU가 없으면 AE에서
Keylight로 같은 구간을 시험합니다. 결과를 검정·흰색·체커 위에서 함께 봅니다.

## 3. 전체 키잉

대상 선택이 맞으면 전체 구간을 백그라운드로 처리합니다. 틀리면 첫 프레임 힌트를 만들어
다시 실행합니다. 장비·스탠드는 키어가 아니라 가비지 마스크로 뺍니다.

## 4. 검수

알파 진단(배경 영역 0, 대상 영역 1 근처), 경계 확대, 재생으로 깜빡임 확인, 출력 전체 디코드.

## 5. AE 합성

`scripts/ae_comp.py`가 만든 JSX로 원본(꺼 둔 비교용)·배경·키 레이어 컴프를 만듭니다. Interpret
Footage(알파 Straight, 픽셀 종횡비, FPS)까지 들어갑니다([AE 컴프 만들기](ae-comp.md)). 그 위에
접지 그림자 → 색·블러·그레인을 맞춥니다. 학생이 렌더하고, 에이전트가 마지막 프레임과 색 태그까지 검수합니다.

## 다음 확장

이번 샷에서 실제로 쓴 단계만 `scripts/`로 옮깁니다. 예: shot.json 작성, CorridorKey 실행
래퍼(자기 코드로 CLI만 호출), 알파 진단. CorridorKey 코드를 복사해 고치는
경우에는 그 라이선스(무료 공개·같은 라이선스·이름 유지)를 따릅니다.
