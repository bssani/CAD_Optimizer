# Lesson Learned — 샘플 레벨의 분포는 실 CAD와 다를 수 있다

> **생성일**: 2026-04-24 (Week 3 / F3 Instance Detection 테스트)
> **원칙**: 샘플 레벨로 얻은 metric은 **기능 동작 증거**일 뿐,
>          **ROI/threshold 근거로 쓰면 안 된다**. 반드시 실 도메인 데이터로 재측정.

---

## 배경

Week 3 F3 Instance Detection 실레벨 테스트에서 Epic Games의 `CarConfigurator` 샘플 프로젝트 레벨을 사용.

결과 (threshold=10):

```
Scanned:  10,107 actors (10,070 StaticMeshActor, 37 other)
Skipped:  0 no-mesh, 0 no-component, 6 non-static
Groups:   21 unique (2 candidates)
  #1  10,000×  /Engine/BasicShapes/Plane [STATIC]
  #2      17×  /Game/.../SM_BGMountain_3 [STATIC]
Est. drawcall reduction: 10,015
Slot mismatches: 0
```

- 21개 그룹 중 단 **2개**만 candidate
- 나머지 19개는 전부 threshold 미만 (≤9×)
- Top 1이 **Plane 10,000×** — 배경 tiling용 합성 중복, 실 CAD엔 존재하지 않는 분포

---

## 문제 제기

이 측정치를 그대로 "F3 ROI = 10,015 draw call 감소"로 일반화하면 **심각한 오해**를 유발한다.

| 관점 | 샘플 레벨 (CarConfigurator) | 실 GM 차량 CAD (예상) |
|------|----------------------------|----------------------|
| 전체 actor | 10,107 | 수만 |
| 그룹 수 | 21 | 수백~수천 |
| 분포 형태 | 극단 long-tail (단일 10K bucket) | 중간 크기 bucket 다수 |
| Top 후보 | Plane 10K× (합성) | Bolt/Nut/Clip 같은 공용 부품 수백~수천× |
| Material mismatch | 0 (Epic 자산 정제도) | 수십~수백 (import 경로 이슈) |
| Threshold 10 적정성 | 2 candidate만 남음 → 지나치게 관대 | 미상 |

핵심: **Threshold 10이 적정한지, ROI 10,015가 대표값인지, mismatch 0이 항상 그런지 — 전부 실 CAD 측정 전엔 판단 불가.**

---

## 교훈

1. **샘플 레벨은 smoke test용**.
   - 기능이 crash 없이 동작하는지, API 호출 순서가 맞는지, 리포트 포맷이 읽히는지 — 여기까지는 충분히 검증됨.
   - 하지만 숫자 자체의 대표성은 **없음**.

2. **모든 metric/threshold는 실 도메인 데이터로 재측정**.
   - Phase 1 exit criteria에 **"실 CAD 1건 이상 측정 완료"** 포함 권장.
   - 재측정 전까진 샘플 수치를 **"참고용, pending"** 으로 명기.

3. **분포 형태 자체가 진단 신호**.
   - 극단 분포(single huge bucket): ISM으로 해결 가능.
   - 정상 분포(many medium buckets): ISM만으론 부족 — naming filter / material consolidation / actor merging 등 복합 처방 필요.
   - Phase 2 scope 결정 시 이 분포 정보가 입력값.

---

## 적용 원칙

- **2단계 검증 의무화**: 모든 Phase 1 feature는
  1. 샘플 레벨 smoke test (crash-free, 포맷 정합성)
  2. 실 CAD 측정 (수치 대표성)
- Week 4~5 F4 / F5 / F6도 동일 원칙.
- 실 CAD 접근 불가 시점엔 PR/로그에 `"샘플 측정치 = 참고용, 실수치 재측정 pending"` 명기.
- Phase 1 완료 보고서 (`Phase1_Completion_Report.md`)에 **샘플 측정 + 실 CAD 측정 양쪽** 기재.

---

## 관련 항목

- Week 3 log: `docs/weekly_log/week03.md`
- CLAUDE.md §4 "Phase별 접근" — Phase 1 = core recipes + infra, 수치는 Phase 1 exit 시점에 실 CAD로 확정.
- (Phase 2 진입 시) 이 lesson을 CLAUDE.md §5 "절대 하지 말 것"에 편입할지 재검토.
