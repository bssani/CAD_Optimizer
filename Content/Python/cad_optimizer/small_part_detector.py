"""Small part detection module — pure logic, no UI.

F4: Find StaticMeshActor with small bbox diagonal (PCVR culling
candidates). Detection-only; the level/actors are never mutated.

Depends only on ``unreal``, ``math``, ``re``, and ``collections``.
UI/progress concerns are injected via callbacks (same pattern as F2
``stats.py`` and F3 ``instance_detector.py``).

Notes:
    - Hierarchy comes from the attach chain. Datasmith CAD import
      does NOT use folder_path (almost always empty Name("None")).
      ``parent_part_label`` and ``parent_chain_path`` columns expose
      the assembly context the leaf actor belongs to.
    - Leaf ``actor_label`` is mostly meaningless for Datasmith CAD
      (~99.98% are auto-generated "Geometry*" prefix in real GM CAD).
      The real part name is on the immediate parent — captured in
      ``parent_part_label``.
    - Disjoint meshes (e.g. left/right symmetric parts merged into a
      single mesh asset) are NOT split here. F4 reports the full bbox
      of such meshes, which can produce false negatives. Multi-leaf
      cases (one logical part split across N leaves, ~9.4% in real
      CAD) are flagged via ``is_multi_leaf`` for user review. Phase 2
      will handle bbox merging.
    - Root-level meshes (no attach parent) are still measured;
      ``skipped_no_attach_parent`` is a visibility counter only.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import unreal


# Threshold presets (cm). 사용자가 직접 수정 가능.
PRESETS: Dict[str, float] = {
    "Tiny": 0.5,    # micro detail (M2 bolt, marker)
    "Small": 1.0,   # 일반 fastener (M3~M5 bolt, 작은 clip)
    "Medium": 5.0,  # 작은 부품 일반 (washer, bracket, small housing)
}

# Multi-threshold simulation 표시 값 (cm). re-threshold simulation은 free.
SIMULATION_THRESHOLDS_CM: List[float] = [0.5, 1.0, 2.0, 5.0, 10.0]

# Chain trim — Datasmith CAD import의 noise label 제거 패턴.
# 실 CAD 검증 (C1YC_2_MCM, 107K actors) 기반.
_CHAIN_NOISE_PATTERNS = (
    re.compile(r'^RootNode(_\d+)?$'),         # RootNode, RootNode_2, ...
    re.compile(r'_asmesh$'),                   # *_asmesh (DatasmithSceneActor)
    re.compile(r'_RotationPivot$'),            # *_RotationPivot
    re.compile(r'^(MOVING|NON_MOVING)_'),      # MOVING_*, NON_MOVING_*
    re.compile(r'^(EXT|INT)_'),                # EXT_*, INT_*
)

# TODO(phase2): connected components for disjoint meshes.
# TODO(phase2): per-parent bbox merging for multi-leaf parts.
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
    # NEW (Datasmith hierarchy context — 실 CAD 검증 (C1YC_2_MCM, 107K actors) 기반)
    parent_part_label: str = ""        # immediate parent label (raw, no filter)
    parent_chain_path: str = ""        # filtered chain "root > ... > immediate_parent"
    parent_leaf_count: int = 0         # set in pass 2
    is_multi_leaf: bool = False        # set in pass 2

    def get_label(self) -> str:
        """Lazy label resolution (F3 lesson — avoid editor round-trip
        until report time)."""
        return self.actor.get_actor_label()


@dataclass
class SmallPartDetectionReport:
    total_actors_scanned: int
    static_mesh_actors: int
    skipped_no_root: int
    skipped_no_mesh: int       # smc None or static_mesh None
    skipped_zero_bbox: int
    skipped_no_attach_parent: int  # root-level mesh.
                                   # ※ MEASURED, not skipped.
                                   # measurements 리스트에 포함됨, 카운트만 별도.
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


# ─── Hierarchy helpers (실 CAD 검증 기반 — Datasmith attach chain) ──


def _is_noise_label(label: str) -> bool:
    """True if the label matches any Datasmith chain noise pattern."""
    return any(p.search(label) for p in _CHAIN_NOISE_PATTERNS)


def _build_parent_chain_path(leaf_actor) -> str:
    """Walk attach chain from immediate parent upward, filter noise,
    return root-first " > "-joined string. Empty string if no parent
    or all labels filtered out.

    Uses a ``while`` loop (NOT recursion) — chain depth is observed up
    to ~13 in real CAD, with theoretical room for 20+. Recursion would
    risk the Python stack limit.

    Example (C1YC_2_MCM real chain, depth 9):
        leaf = Geometry6 (StaticMeshActor)
        Parent chain (leaf→root):
          [1] 26514648_001_0002-STRUT_ASM-L_GATE__FIEDERBEIN__973666  ← keep
          [2] RH_Strut_Upper_C1YC-2_MCM                                ← keep
          [3] RH_Strut_Upper_Trans_C1YC-2_MCM                          ← keep
          [4] 55_2_2                                                    ← keep
          [5] NON_MOVING_C1YC-2_MCM                                     ← drop
          [6] NON_MOVING_C1YC-2_MCM_RotationPivot                       ← drop
          [7] RootNode_2                                                ← drop
          [8] NON_MOVING_C1YC-2_MCM_asmesh                              ← drop
        Result (root→leaf):
          "55_2_2 > RH_Strut_Upper_Trans_C1YC-2_MCM > "
          "RH_Strut_Upper_C1YC-2_MCM > "
          "26514648_001_0002-STRUT_ASM-L_GATE__FIEDERBEIN__973666"
    """
    labels: List[str] = []
    cur = leaf_actor.get_attach_parent_actor()
    while cur is not None:
        label = cur.get_actor_label()
        if not _is_noise_label(label):
            labels.append(label)
        cur = cur.get_attach_parent_actor()
    if not labels:
        return ""
    return " > ".join(reversed(labels))


# ─── Public API ─────────────────────────────────────────────────────


def detect_small_parts(
    actors: list,
    threshold_cm: float = 1.0,
    should_cancel: Callable[[], bool] = lambda: False,
    on_progress: Callable[[], None] = lambda: None,
) -> SmallPartDetectionReport:
    """Walk ``actors`` and measure bbox diagonals + assembly context.
    Dry-run; the level is never mutated.

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
        - non-StaticMeshActor: silently absorbed by ``total_actors_scanned``
          (no dedicated field)
        - no root component: ``skipped_no_root``
        - no SMC / no static_mesh asset: ``skipped_no_mesh``
        - all-zero half-extent: ``skipped_zero_bbox``
        - no attach parent (root-level mesh): ``skipped_no_attach_parent``
          ※ MEASURED — count only, NOT excluded from measurements list

    Two-pass:
        Pass 1 walks actors, measures bboxes, captures attach parents.
        Pass 2 tallies sibling counts per parent (Counter) and stamps
        ``parent_leaf_count`` / ``is_multi_leaf`` onto each measurement.

    Empty input is safe: every list/min/max/Counter site is guarded.
    """
    measurements: List[SmallPartMeasurement] = []
    leaf_to_parent: Dict[unreal.Actor, Optional[unreal.Actor]] = {}

    total = 0
    sma_count = 0
    no_root = 0
    no_mesh = 0
    zero_bbox = 0
    no_attach_parent = 0

    # ─── Pass 1: measure + collect parent info ───
    for actor in actors:
        if should_cancel():
            break

        total += 1

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

        # Attach parent + filtered chain (Datasmith hierarchy context)
        parent_actor = actor.get_attach_parent_actor()
        if parent_actor is None:
            no_attach_parent += 1
            parent_label = ""
            chain_path = ""
        else:
            parent_label = parent_actor.get_actor_label()
            chain_path = _build_parent_chain_path(actor)

        leaf_to_parent[actor] = parent_actor  # value may be None

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
                parent_part_label=parent_label,
                parent_chain_path=chain_path,
                # parent_leaf_count / is_multi_leaf set in pass 2
            )
        )

        on_progress()

    # ─── Pass 2: count siblings per parent ───
    # Counter(<empty_iter>) is safe — produces empty Counter. The
    # all-root-level case yields no entries here; the loop below then
    # writes count=1 for every measurement (fall-through branch).
    parent_leaf_counts = Counter(
        p for p in leaf_to_parent.values() if p is not None
    )
    for m in measurements:
        parent = leaf_to_parent.get(m.actor)
        if parent is None:
            m.parent_leaf_count = 1
            m.is_multi_leaf = False
        else:
            m.parent_leaf_count = parent_leaf_counts[parent]
            m.is_multi_leaf = m.parent_leaf_count > 1

    measurements.sort(key=lambda m: m.bbox_diagonal_cm)

    return SmallPartDetectionReport(
        total_actors_scanned=total,
        static_mesh_actors=sma_count,
        skipped_no_root=no_root,
        skipped_no_mesh=no_mesh,
        skipped_zero_bbox=zero_bbox,
        skipped_no_attach_parent=no_attach_parent,
        measurements=measurements,
        threshold_cm=threshold_cm,
    )
