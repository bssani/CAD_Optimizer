"""Actor Merger — Phase 2 첫 task (ISM 변환).

F3 ``InstanceDetectionReport`` 의 candidate group을 ISM (Instanced Static
Mesh Component) actor 1개 + per-instance transform N개로 변환.

설계 원칙 (F8 패턴 재사용):
- ``select_merge_groups`` / ``plan_merge`` / 박제 = 순수 함수 (``unreal``
  의존 0). 단위 테스트 + CI 가능.
- ``apply_merge_plans`` = mutation. ``unreal`` 의존 (Phase 2 mutation
  본 task).
- Module 자체는 ``import unreal`` 0 — actor 객체는 duck-typed.

Idempotent 전략:
- F8 같은 tag-level fast path 아님 (actor delete = destructive).
- 자연 idempotent: 머지된 ISM holder는 ``unreal.Actor`` (NOT
  ``StaticMeshActor``) 이므로 F3 ``_is_static_mesh_actor`` 체크에서 skip.
  Re-run 시 같은 group의 actor 수 줄어듦 → candidate 자격 잃음 → no-op.
- Sentinel tag ``CADOpt_P2_Merged_*`` = 박제/감사용 (idempotent 아님). 어떤
  ISM이 merger 산출물인지 추적.

박제 reference:
- ``docs/measurements/integrated_report_c1yc_2_mcm.md`` § 3 — F3 candidate
  baseline (303 group, est. 6,196 drawcall ↓).
- ``docs/phase2_backlog.md`` — Phase 2 진입 결정 박제.

Out of scope (이번 task):
- MOVABLE / STATIONARY group (F3 자동 STATIC only).
- Multi-section material complexity-aware drawcall 추정 정밀화 (backlog).
- HISMC LOD 계층 (Nanite가 LOD 처리).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

if TYPE_CHECKING:
    # 타입 힌트만. 런타임 import 없음 (F-pattern: 모듈은 unreal 의존 0).
    from cad_optimizer.instance_detector import (
        InstanceDetectionReport,
        InstanceGroup,
    )


# ─── Constants ──────────────────────────────────────────────────────


# Sentinel tag prefix — F8 `CADOpt_F8_` 패턴 일관. P2 = Phase 2.
TAG_PREFIX = "CADOpt_P2_"

# ISM holder actor에 부여될 tag 형식.
# - {hash} = mesh_path SHA1 앞 8자
# - {count} = 머지된 instance 수
TAG_MERGED_FMT = "CADOpt_P2_Merged_{hash}"
TAG_SOURCE_COUNT_FMT = "CADOpt_P2_SourceCount_{count}"

# 기본 머지 threshold — F3 candidate threshold (≥ 10) 와 일관.
DEFAULT_MERGE_THRESHOLD = 10


# ─── Plan dataclasses ────────────────────────────────────────────────


@dataclass
class MergePlan:
    """단일 group의 머지 계획 (mutation 전 pre-compute).

    Apply 단계에서 추가 계산 없이 그대로 ISM spawn에 사용. dry-run 시 plan만
    출력하면 그대로 박제 가능.
    """

    mesh_path: str
    materials: Tuple[str, ...]
    instance_count: int
    pivot_location: Tuple[float, float, float]  # ISM holder actor 위치 (centroid)
    source_actors: List[Any] = field(default_factory=list)  # duck-typed actor 참조
    # actor.get_actor_transform() 결과를 pivot 기준 relative로 변환한 transform.
    # apply 시 ISMC.add_instance() 에 그대로 넘김. Length == instance_count.
    relative_transforms: List[Any] = field(default_factory=list)
    mesh_short_hash: str = ""  # SHA1[:8] of mesh_path — sentinel tag용

    @property
    def estimated_drawcall_reduction(self) -> int:
        """이 plan의 drawcall 감소 (F3 공식 일관: (count-1) * num_materials)."""
        return (self.instance_count - 1) * len(self.materials)


@dataclass
class MergeResult:
    """Apply 결과 — Output Log + CSV 박제 입력."""

    plans_total: int = 0
    plans_applied: int = 0   # spawn + delete 성공한 plan 수
    plans_skipped: int = 0   # actor invalid / API failure 등
    instances_merged: int = 0
    actors_deleted: int = 0
    estimated_drawcall_reduction: int = 0
    csv_path: str = ""
    dry_run: bool = False


# ─── Pure: group selection ──────────────────────────────────────────


def select_merge_groups(
    report: "InstanceDetectionReport",
    threshold: int = DEFAULT_MERGE_THRESHOLD,
) -> List["InstanceGroup"]:
    """F3 report에서 머지 대상 group 선별.

    F3 ``candidate_groups`` 의 superset (threshold만 다름). F3 default
    threshold (10) 와 같으면 결과 동일.

    필터:
    - count >= threshold (단일 instance는 머지 의미 없음 — 최소 2)
    - mobility STATIC 보장 (F3에서 자동 보장, 추가 체크 없음)
    """
    effective_threshold = max(threshold, 2)
    return [g for g in report.groups if g.count >= effective_threshold]


# ─── Pure-ish: pivot + transform computation ─────────────────────────


def compute_pivot(actor_locations: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    """Group actor들의 centroid (axis-aligned, 단순 평균).

    ISM holder actor 의 world location 으로 사용. 인스턴스 transform은 이
    pivot 기준 relative — VR 환경에서 floating-point precision 보존.

    빈 list는 (0, 0, 0) 반환 (defensive).
    """
    n = len(actor_locations)
    if n == 0:
        return (0.0, 0.0, 0.0)
    sx = sum(loc[0] for loc in actor_locations)
    sy = sum(loc[1] for loc in actor_locations)
    sz = sum(loc[2] for loc in actor_locations)
    return (sx / n, sy / n, sz / n)


def _mesh_short_hash(mesh_path: str) -> str:
    """SHA1 앞 8자 — sentinel tag에 박을 mesh identifier.

    Path 그대로 박으면 tag 길이 폭발 + 특수문자. Hash로 안정.
    """
    import hashlib
    return hashlib.sha1(mesh_path.encode("utf-8")).hexdigest()[:8]


def plan_merge(
    report: "InstanceDetectionReport",
    threshold: int = DEFAULT_MERGE_THRESHOLD,
    actor_location_fn: Callable[[Any], Tuple[float, float, float]] = None,  # type: ignore[assignment]
    actor_relative_transform_fn: Callable[[Any, Tuple[float, float, float]], Any] = None,  # type: ignore[assignment]
) -> List[MergePlan]:
    """선별된 group에 대해 ``MergePlan`` 생성.

    Args:
        report: F3 ``InstanceDetectionReport``.
        threshold: ``select_merge_groups`` 임계.
        actor_location_fn: actor 객체 → ``(x, y, z)`` world location 추출.
            테스트에선 stub, 런타임은 panel.py가 ``unreal.Actor.get_actor_location``
            을 wrap해서 주입.
        actor_relative_transform_fn: ``(actor, pivot) -> unreal.Transform``
            (또는 동등 객체). pivot 기준 relative transform 계산. 런타임에
            panel.py에서 주입.

    Returns:
        plan list (group 순서 그대로 — F3는 count desc 정렬).

    Apply 전 dry-run 시 plan 출력만으로 검증 가능. Group 객체 의존 X,
    actor 의존도 callable 통해서만 — pure에 가깝.
    """
    if actor_location_fn is None or actor_relative_transform_fn is None:
        raise ValueError(
            "actor_location_fn and actor_relative_transform_fn must be provided"
            " (panel.py injects unreal-bound wrappers)."
        )

    groups = select_merge_groups(report, threshold)
    plans: List[MergePlan] = []
    for g in groups:
        locations = [actor_location_fn(a) for a in g.actors]
        pivot = compute_pivot(locations)
        rel_transforms = [
            actor_relative_transform_fn(a, pivot) for a in g.actors
        ]
        plans.append(
            MergePlan(
                mesh_path=g.key.mesh_path,
                materials=g.key.materials,
                instance_count=g.count,
                pivot_location=pivot,
                source_actors=list(g.actors),
                relative_transforms=rel_transforms,
                mesh_short_hash=_mesh_short_hash(g.key.mesh_path),
            )
        )
    return plans


# ─── Mutation: apply (skeleton, API verified 후 채움) ──────────────


def apply_merge_plans(
    plans: List[MergePlan],
    dry_run: bool = True,
    csv_out_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], bool]] = None,
    plugin_commit: str = "",
    # Mutation callable 주입 — panel.py가 unreal-bound wrapper 주입.
    spawn_ism_holder_fn: Optional[Callable[..., Any]] = None,
    add_instances_to_ismc_fn: Optional[Callable[..., int]] = None,
    set_ismc_material_fn: Optional[Callable[..., None]] = None,
    destroy_actor_fn: Optional[Callable[[Any], None]] = None,
    tag_actor_fn: Optional[Callable[..., None]] = None,
) -> MergeResult:
    """Plan 리스트 실행.

    NOTE: 이 함수는 ``unreal`` import 0 유지 위해 mutation을 모두 callable
    주입으로 처리. panel.py가 wrapper 작성. API verification 결과 확정 후
    내부 구현 확장.

    Dry-run 모드:
    - spawn / add_instance / destroy 호출 없음
    - plan 통계만 집계 + CSV 박제

    Real-run 모드:
    - 각 plan마다:
      1. ISM holder actor spawn (pivot location)
      2. ISMC에 mesh + materials 설정
      3. relative_transforms를 add_instances로 일괄 추가
      4. holder에 sentinel tag 부여
      5. source_actors 모두 destroy
    - Single ScopedSlowTask, cancel 시 현재 plan 끝까지 진행 후 중단
    """
    result = MergeResult(
        plans_total=len(plans),
        dry_run=dry_run,
    )

    # API verification 결과 받기 전까진 real-run 진입 차단.
    # 의도된 lock — 실수로 production 환경에서 호출되어도 destructive 작업 없음.
    if not dry_run:
        if any(
            fn is None
            for fn in (
                spawn_ism_holder_fn,
                add_instances_to_ismc_fn,
                set_ismc_material_fn,
                destroy_actor_fn,
                tag_actor_fn,
            )
        ):
            raise NotImplementedError(
                "Real-run mode requires all mutation callables injected from"
                " panel.py (pending UE API verification on Philip's machine)."
            )

    for i, plan in enumerate(plans):
        if progress_callback is not None:
            try:
                cont = progress_callback(
                    i, len(plans),
                    f"Merging {i + 1}/{len(plans)}: {plan.mesh_path}"
                )
            except Exception:
                cont = True
            if cont is False:
                break

        if dry_run:
            # 통계만 집계
            result.plans_applied += 1
            result.instances_merged += plan.instance_count
            result.estimated_drawcall_reduction += plan.estimated_drawcall_reduction
            continue

        # Real-run: 1 plan = 1 ISM holder spawn + N instance + N source delete.
        # 실패 시 해당 plan만 skip (다른 plan 진행). holder는 spawn 함수가
        # 내부 cleanup 책임 (mesh asset missing 등 early failure 케이스).
        try:
            holder, ismc = spawn_ism_holder_fn(  # type: ignore[misc]
                plan.mesh_path, plan.pivot_location
            )
            set_ismc_material_fn(ismc, list(plan.materials))  # type: ignore[misc]
            add_instances_to_ismc_fn(ismc, plan.relative_transforms)  # type: ignore[misc]
            tag_actor_fn(holder, plan.mesh_short_hash, plan.instance_count)  # type: ignore[misc]
            destroy_actor_fn(plan.source_actors)  # type: ignore[misc]

            result.plans_applied += 1
            result.instances_merged += plan.instance_count
            result.actors_deleted += plan.instance_count
            result.estimated_drawcall_reduction += (
                plan.estimated_drawcall_reduction
            )
        except Exception:
            # spawn / mesh load / API 실패 — 통계만 기록, 다음 plan 계속.
            # 디버깅 콜백을 callable로 받지 않으므로 detail은 caller (panel.py)
            # 가 별도 logging해야 함. Phase 2 후반에 plan-level result list로
            # 노출 검토 (backlog).
            result.plans_skipped += 1

    if csv_out_path:
        _write_csv(csv_out_path, plans, result, plugin_commit)
        result.csv_path = csv_out_path.replace("\\", "/")

    return result


# ─── CSV 박제 ──────────────────────────────────────────────────────


def _write_csv(
    path: str,
    plans: List[MergePlan],
    result: MergeResult,
    plugin_commit: str,
) -> None:
    """Merge plan CSV — F4/F6/F8 패턴 일관 (# 4줄 + writer header)."""
    import csv as csv_mod
    import os
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_str = plugin_commit if plugin_commit else "(미지정)"
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    mode = "dry-run" if result.dry_run else "applied"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(f"# Actor Merger (Phase 2) — generated {ts}\n")
        f.write(f"# Plugin commit: {commit_str}\n")
        f.write(f"# Mode: {mode}\n")
        f.write(
            f"# Plans: {result.plans_total} "
            f"(applied: {result.plans_applied}, "
            f"skipped: {result.plans_skipped}) | "
            f"instances merged: {result.instances_merged} | "
            f"est. drawcall ↓: {result.estimated_drawcall_reduction}\n"
        )
        writer = csv_mod.writer(f)
        writer.writerow([
            "mesh_path",
            "mesh_short_hash",
            "instance_count",
            "num_materials",
            "pivot_x",
            "pivot_y",
            "pivot_z",
            "est_drawcall_reduction",
        ])
        for plan in plans:
            writer.writerow([
                plan.mesh_path,
                plan.mesh_short_hash,
                plan.instance_count,
                len(plan.materials),
                f"{plan.pivot_location[0]:.3f}",
                f"{plan.pivot_location[1]:.3f}",
                f"{plan.pivot_location[2]:.3f}",
                plan.estimated_drawcall_reduction,
            ])
