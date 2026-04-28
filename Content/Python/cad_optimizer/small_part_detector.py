"""Small part detection module — pure logic, no UI.

F4: Find StaticMeshActor with small bbox diagonal (PCVR culling
candidates). Detection-only; the level/actors are never mutated.

Depends only on ``unreal`` and ``math``. UI/progress concerns are
injected via callbacks (same pattern as F2 ``stats.py`` and F3
``instance_detector.py``).

Notes:
    - InstancedStaticMeshActor (ISMA) is intentionally skipped. ISMA
      bbox represents the entire instance cluster, not individual
      instances — not aligned with F4 intent. Phase 2 will handle
      ISMA per-instance.
    - Disjoint meshes (e.g. left/right symmetric parts merged into a
      single mesh asset) are NOT split here. F4 reports the full bbox
      of such meshes, which can produce false negatives — see Phase 2
      backlog. The caller (panel.py) emits a one-paragraph warning
      after every scan to keep this caveat visible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import unreal


# Threshold presets (cm). 사용자가 직접 수정 가능.
PRESETS: Dict[str, float] = {
    "Tiny": 0.5,    # micro detail (M2 bolt, marker)
    "Small": 1.0,   # 일반 fastener (M3~M5 bolt, 작은 clip)
    "Medium": 5.0,  # 작은 부품 일반 (washer, bracket, small housing)
}

# Multi-threshold simulation 표시 값 (cm). re-threshold simulation은 free.
SIMULATION_THRESHOLDS_CM: List[float] = [0.5, 1.0, 2.0, 5.0, 10.0]

# TODO(phase2): connected components for disjoint meshes.
# TODO(phase2): InstancedStaticMeshActor handling (per-instance bbox).
# TODO(phase2): density ratio (mesh_volume / bbox_volume) for disjoint suspects.
# TODO(phase2 검토): vertex/triangle count column (현재는 F2 결과와
#                    mesh_path join으로 사후 분석 가능).


@dataclass
class SmallPartMeasurement:
    """Per-actor bbox measurement. Raw values retained so callers can
    re-threshold without rescanning."""

    actor: unreal.Actor
    mesh_path: str
    folder_path: str        # outliner folder; "" if root-level
    mobility_name: str
    bbox_x_cm: float
    bbox_y_cm: float
    bbox_z_cm: float
    bbox_diagonal_cm: float
    bbox_max_edge_cm: float
    bbox_volume_cm3: float

    def get_label(self) -> str:
        """Lazy label resolution (F3 lesson — avoid editor round-trip
        until report time)."""
        return self.actor.get_actor_label()


@dataclass
class SmallPartDetectionReport:
    total_actors_scanned: int
    static_mesh_actors: int
    skipped_isma: int          # InstancedStaticMeshActor — 의도적 skip
    skipped_no_root: int
    skipped_no_mesh: int       # smc None or static_mesh None
    skipped_zero_bbox: int
    measurements: List[SmallPartMeasurement]  # sorted by diagonal asc
    threshold_cm: float

    def is_small(self, m: SmallPartMeasurement) -> bool:
        return m.bbox_diagonal_cm < self.threshold_cm

    @property
    def small_parts(self) -> List[SmallPartMeasurement]:
        return [m for m in self.measurements if self.is_small(m)]

    @property
    def diagonal_percentiles(self) -> Dict[str, float]:
        """P10 / P50 / P90 of diagonals. Empty dict if no measurements."""
        if not self.measurements:
            return {}
        diags = sorted(m.bbox_diagonal_cm for m in self.measurements)
        n = len(diags)
        return {
            "p10": diags[int(n * 0.10)],
            "p50": diags[int(n * 0.50)],
            "p90": diags[min(int(n * 0.90), n - 1)],
        }

    def simulate_thresholds(
        self, thresholds_cm: List[float]
    ) -> List[Tuple[float, int]]:
        """Re-threshold without rescanning.

        Returns ``[(threshold_cm, count_below), ...]`` sorted by threshold
        asc. Always returns one row per input threshold, even with no
        measurements (count=0).
        """
        sorted_thresholds = sorted(thresholds_cm)
        if not self.measurements:
            return [(t, 0) for t in sorted_thresholds]
        sorted_diags = sorted(m.bbox_diagonal_cm for m in self.measurements)
        return [(t, sum(1 for d in sorted_diags if d < t)) for t in sorted_thresholds]


# ─── UE API isolation layer ─────────────────────────────────────────
# Future UE version bumps (5.6+) touch only this block.


def _is_isma(actor) -> bool:
    return isinstance(actor, unreal.InstancedStaticMeshActor)


def _is_static_mesh_actor(actor) -> bool:
    return isinstance(actor, unreal.StaticMeshActor)


def _get_root_component(actor):
    return actor.root_component


def _get_static_mesh_component(actor):
    return actor.static_mesh_component


def _get_static_mesh(smc):
    return smc.static_mesh


def _get_actor_bounds(actor):
    """Returns ``(origin: Vector, extent: Vector)`` — extent is half-extent.

    ``only_colliding_components=False`` so non-colliding meshes still
    produce a bbox (most CAD imports don't auto-generate collision).
    """
    return actor.get_actor_bounds(only_colliding_components=False)


def _get_folder_path_str(actor) -> str:
    """``get_folder_path`` returns ``unreal.Name``; can be None or empty."""
    raw = actor.get_folder_path()
    if raw is None:
        return ""
    s = str(raw)
    return "" if s == "None" else s


def _mobility_name(rc) -> str:
    return rc.mobility.name


def _mesh_path(sm) -> str:
    return sm.get_path_name()


# ─── Public API ─────────────────────────────────────────────────────


def detect_small_parts(
    actors: list,
    threshold_cm: float = 1.0,
    should_cancel: Callable[[], bool] = lambda: False,
    on_progress: Callable[[], None] = lambda: None,
) -> SmallPartDetectionReport:
    """Walk ``actors`` and measure bbox diagonals. Dry-run.

    Args:
        actors: output of ``EditorActorSubsystem.get_all_level_actors()``.
        threshold_cm: stored on the report; ``small_parts`` filter and the
            UI's ``[Preset: ...]`` matching use this value. ``measurements``
            is unconditional — re-thresholding via ``simulate_thresholds``
            is free (no rescan).
        should_cancel: polled once per iteration. True → break, return
            partial report. The function does not record a cancelled flag;
            the caller captures cancellation externally (closure flag).
        on_progress: called once per actor iteration including skipped
            ones (uniform progress). Cancelled iteration forgoes the tick.

    Skip categories (counted in the report):
        - ISMA: ``skipped_isma`` (intentional — ISMA bbox is cluster-wide)
        - non-StaticMeshActor: silently absorbed by ``total_actors_scanned``
          (no dedicated field — cheap UE actor types like Light fall here)
        - no root component: ``skipped_no_root``
        - no SMC / no static_mesh asset: ``skipped_no_mesh``
        - all-zero half-extent: ``skipped_zero_bbox``

    Empty input is safe: every list/min/max site is guarded.
    """
    measurements: List[SmallPartMeasurement] = []
    total = 0
    sma_count = 0
    isma_count = 0
    no_root = 0
    no_mesh = 0
    zero_bbox = 0

    for actor in actors:
        if should_cancel():
            break

        total += 1

        # ISMA first — separate UClass, isinstance(...StaticMeshActor) is
        # already false for it but the explicit branch keeps the count
        # honest and the intent visible.
        if _is_isma(actor):
            isma_count += 1
            on_progress()
            continue

        if not _is_static_mesh_actor(actor):
            on_progress()
            continue

        sma_count += 1

        rc = _get_root_component(actor)
        if rc is None:
            no_root += 1
            on_progress()
            continue

        smc = _get_static_mesh_component(actor)
        if smc is None:
            no_mesh += 1
            on_progress()
            continue

        sm = _get_static_mesh(smc)
        if sm is None:
            no_mesh += 1
            on_progress()
            continue

        _origin, extent = _get_actor_bounds(actor)
        if extent.x == 0 and extent.y == 0 and extent.z == 0:
            zero_bbox += 1
            on_progress()
            continue

        bx = extent.x * 2.0
        by = extent.y * 2.0
        bz = extent.z * 2.0
        diagonal = math.sqrt(bx * bx + by * by + bz * bz)
        max_edge = max(bx, by, bz)
        volume = bx * by * bz

        measurements.append(
            SmallPartMeasurement(
                actor=actor,
                mesh_path=_mesh_path(sm),
                folder_path=_get_folder_path_str(actor),
                mobility_name=_mobility_name(rc),
                bbox_x_cm=bx,
                bbox_y_cm=by,
                bbox_z_cm=bz,
                bbox_diagonal_cm=diagonal,
                bbox_max_edge_cm=max_edge,
                bbox_volume_cm3=volume,
            )
        )

        on_progress()

    measurements.sort(key=lambda m: m.bbox_diagonal_cm)

    return SmallPartDetectionReport(
        total_actors_scanned=total,
        static_mesh_actors=sma_count,
        skipped_isma=isma_count,
        skipped_no_root=no_root,
        skipped_no_mesh=no_mesh,
        skipped_zero_bbox=zero_bbox,
        measurements=measurements,
        threshold_cm=threshold_cm,
    )
