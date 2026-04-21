# Lessons Learned: Decimation 함정

> 우리 프로젝트 맥락에서 decimation 접근 시 주의사항 기록.
> 새 팀원 합류 시 또는 Phase 3에서 decimation 도입 고려 시 먼저 읽을 것.

---

## 이미 시도해본 실패 사례 (2026-04-18 기준)

필립이 본 프로젝트 이전에 겪은 실패 사례:

### 시도한 방법
- **도구**: UE 5.5 내장 Reduce / Mesh Editor의 Simplify
- **대상**: 전체 차량 한꺼번에
- **Nanite 상태**: 꺼둔 채로 시도

### 결과
- Mesh 대량 깨짐
- 대시보드 버튼, 작은 trim 같은 fine detail이 뭉개짐
- 일부 mesh는 hole 생김

### 진단된 원인

**1. 도구 선택 미스매치**
- UE 내장 Reduce는 **game-ready asset** (이미 정리된 mesh) 용으로 튜닝됨
- CAD tessellation에서 바로 넘어온 mesh에 부적합:
  - Sharp edge preservation 옵션 GUI 노출 약함
  - Non-manifold 입력 robust하지 않음
  - UV seam / material boundary 보호 약함
  - T-junction, coplanar face 대응 없음

**2. 전체 scene 한 번에 처리**
- 알고리즘이 "중요한 feature"를 scene 기준으로 판단
- 눈에 띄는 큰 panel만 보존 → 작은 part (핸들, 스위치)는 "덜 중요"로 처리되어 뭉개짐

**3. Nanite 비활성화**
- Nanite는 이미 cluster 기반 자동 LOD 시스템
- 끄면 자동 LOD 이점 소멸
- 수동 decimation + Nanite 끔 = self-sabotage

---

## Decimation 올바른 방법 (우리 프로젝트 기준)

**기본 원칙: Nanite를 먼저 최대한 활용. Decimation은 최후의 수단.**

**그래도 필요하면:**

1. **대상을 좁혀라**
   - 전체 차량 금지
   - "Nanite 못 쓰는 mesh만" (masked material, translucent, two-sided, skeletal)
   - 차량 전체의 5~10% 수준

2. **Repair 먼저**
   - Hole fill
   - Duplicate vertex merge
   - Zero-area face 제거
   - Normal 재계산
   - 이거 없이 decimation = 깨짐 확정

3. **Part 단위 개별 처리**
   - 각 mesh의 크기/역할에 맞게 ratio 차등
   - 도어 패널 30% 감축 OK, 버튼 0~10%, 로고 건드리지 말 것

4. **Iterative 적용**
   - 90% 한 번 > 50% × 3회
   - 점진적이 훨씬 안정적

5. **Feature preservation 설정**
   - Crease angle threshold
   - UV seam preservation
   - Material boundary preservation

---

## 권장 도구 (라이선스 안전한 것만)

| 도구 | 라이선스 | 적합성 |
|------|----------|--------|
| **Open3D** | MIT | ⭐ 1순위. Python API 깔끔, repair 함수 포함 |
| **trimesh** | MIT | ⭐ Python 순수, 간편 |
| **meshoptimizer** | MIT | GPU-friendly reordering |
| UE 내장 Reduce | - | ⚠️ CAD mesh 부적합 |
| MeshLib | non-commercial | ❌ 상용 사용 불가 |
| PyMeshLab / VCGlib | GPL 3 | ⚠️ 사내만 OK, 배포 시 전염 |
| CGAL | GPL / 상용 이중 | ⚠️ 상용 유료 |

---

## 언제 이 문서 다시 볼 것인가

- Phase 1 완료 후 측정 결과 draw call 최적화만으로 부족할 때
- Phase 3에서 visibility culling 끝낸 후 "Nanite 못 쓰는 mesh" 처리 필요할 때
- 새 팀원이 "decimation 안 해봐?" 할 때

---

*작성일: 2026-04-18*
*다음 업데이트: 실제 Open3D 기반 decimation 시도 후*
