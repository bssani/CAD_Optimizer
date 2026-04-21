# ADR-001: Python Only, No C++

**Status**: Accepted
**Date**: 2026-04-18
**Context**: Phase 1 setup

## 배경

Plugin 구현 언어로 Python only vs Python + C++ 혼합 vs C++ only 중 선택 필요.

## 결정

**Phase 1~2는 Python only로 간다.** C++는 도입하지 않음.

## 고려한 옵션

### Option A: Python only (채택)
- **장점**:
  - 컴파일 불필요, 배포 단순 (폴더 복사만)
  - 필립이 이미 Python 숙련
  - UE Python API로 Phase 1~2 기능 커버 가능
  - hot reload로 빠른 iteration
  - Visual Studio 설정 불필요
- **단점**:
  - 실행 속도 Python 수준 (대규모 scene에선 체감될 수 있음)
  - 일부 고급 API는 C++ 전용
  - Slate UI 불가 (UMG로 대체)

### Option B: Python + C++ 혼합
- **장점**: 성능 critical 부분만 C++로
- **단점**:
  - 빌드 파이프라인 복잡
  - Visual Studio 환경 설정 필요
  - 다른 PC 배포 시 precompiled binary 필요
  - 학습 곡선 급증

### Option C: C++ only
- **장점**: 최고 성능, full API access
- **단점**:
  - Phase 1 기능엔 overkill
  - 개발 속도 크게 저하
  - 학습 목표와 배치

## 의사결정 근거

- **Phase 1~2 기능은 mesh 순회 + metadata 조작이 주력**이고, 내부 heavy lifting은 UE 엔진이 C++로 처리함. Python wrapper는 호출만 하므로 성능 병목 없음
- 배포 단순성 > 성능. PQDQ 팀뿐 아니라 다른 부서 배포 목표라 "압축 풀면 동작" 수준이어야 함
- 필립의 Python 숙련도 활용. C++ 병행 학습은 프로젝트 리스크

## 재검토 시점

- Phase 3에서 visibility culling 구현 시 ray casting 성능 이슈 발생하면 해당 기능만 C++ 고려
- 30,000 mesh 실제 처리 시 눈에 띄는 지연 (> 수 분) 발생 시 재평가

## 참고

- UE Python Scripting: https://docs.unrealengine.com/5.5/en-US/scripting-the-unreal-editor-using-python/
