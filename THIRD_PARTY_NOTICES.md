# 출처와 별도 라이선스

이 저장소의 새 starter 코드와 문서는 [MIT](LICENSE)입니다. 아래 외부 도구·모델·영상은
**이 저장소에 포함하지 않으며**, 각자의 라이선스를 따릅니다. MIT는 이 저장소에서 새로 쓴
문서와 설치 점검 스크립트에만 적용됩니다.

## CorridorKey 2.0

- 출처: https://github.com/nikopueringer/CorridorKey2.0 (기준 commit `485f5e9ab759ead6138cc990776184b59d6ea971`),
  가중치 https://huggingface.co/nikopueringer/CorridorKey2.0
- 제작: Zachary Harris, Niko, Corridor Digital
- 라이선스: Corridor Key Licence — CC BY-NC-SA 4.0의 변형에 추가 조건.
  상업 영상 처리 사용 가능. 도구 판매·코드/모델 유료 접근·허가 없는 유료 API/추론 서비스 금지.
  수정본 공개 시 무료 공개·같은 라이선스·CorridorKey 이름 유지. 연 매출 2천만 달러 초과
  조직은 사용자별 플러그인 좌석 필요. 원문: https://github.com/nikopueringer/CorridorKey2.0/blob/master/LICENSE
- 이 저장소는 CorridorKey의 코드·가중치를 복사·수정·재배포하지 않고, 공식 설치 방법만 안내합니다.

## CorridorKey가 내려받는 기반 모델

| 모델 | 출처 | 라이선스 |
| --- | --- | --- |
| C-RADIOv4-SO400M | https://huggingface.co/nvidia/C-RADIOv4-SO400M | NVIDIA Open Model License |
| MoGe-2 ViT-B | https://github.com/microsoft/MoGe | MIT(코드·가중치), 포함된 DINOv2 코드 Apache-2.0 |
| RVM small | https://github.com/google-deepmind/representations4d | 코드 Apache-2.0, 가중치 CC-BY 4.0 |

## 연습·배경 영상

| 소스 | 출처 | 조건 |
| --- | --- | --- |
| Hollywood Camera Work 그린스크린 플레이트 | https://www.hollywoodcamerawork.com/green-screen-plates.html | 로컬 연습 허용, 원본 재호스팅·직접 다운로드 링크 게시 금지. 공개 전 페이지 조건 재확인 |
| Poly Haven(배경 예) | https://polyhaven.com/license | CC0 |

## 그 밖의 도구

| 도구 | 공식 출처 | 배포 범위 |
| --- | --- | --- |
| After Effects(Keylight 포함) | https://www.adobe.com/products/aftereffects.html | 상용, 학생의 별도 라이선스 필요 |
| PyTorch | https://github.com/pytorch/pytorch/blob/main/LICENSE | BSD-3-Clause; CorridorKey 환경에 pip 설치 |
| FFmpeg | https://ffmpeg.org/legal.html | 빌드 옵션에 따라 LGPL/GPL 등 확인; 바이너리 미포함 |
| NumPy | https://github.com/numpy/numpy/blob/main/LICENSE.txt | BSD-3-Clause; pip 설치 |
| Pillow | https://pillow.readthedocs.io/en/stable/about.html#license | MIT-CMU; pip 설치 |

## 참고한 기록

2026-10-26 Codex 세션 "CorridorKey 2.0 키잉 테스트"(공개 연습 영상 5개, 520프레임, RTX 4070 Ti
SUPER 16GB)와 [hyun2xyz/vfx-workbench](https://github.com/hyun2xyz/vfx-workbench)의 키잉 기록에서
규칙을 축약했습니다. 테스트 영상·결과·녹화는 포함하지 않았습니다.
