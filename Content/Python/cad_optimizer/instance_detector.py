"""Instance detection module — pure logic, no UI.

F3: Find StaticMeshActor groups that could benefit from ISM conversion.

This module depends only on ``unreal``. UI/progress concerns are injected
via callbacks (same pattern as F2 ``stats.py``). All direct ``unreal.*``
calls live in the ``_get_*`` / ``_is_*`` helpers below so 5.6+
deprecation only touches that block.

Report is detection-only: the level/actors are never mutated.
ISM/HISM conversion is Phase 2 scope; this module is the signal that
decides where conversion is worth doing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Tuple

import unreal

# TODO(phase2): parent actor / sub-level awareness for ISM eligibility filtering.
# TODO(phase2): section count-based draw call refinement with material complexity.


_MATERIAL_MISMATCH_WARNING_CAP = 5


@dataclass(frozen=True)
class InstanceGroupKey:
    """Hashable grouping key for ISM candidate detection."""

    mesh_path: str
    materials: Tuple[str, ...]  # override-resolved material path names
    mobility_name: str  # 'STATIC' | 'MOVABLE' | 'STATIONARY'


@dataclass
class InstanceGroup:
    """Group of StaticMeshActor sharing the same InstanceGroupKey.

    Actor references are retained (not labels) to defer expensive
    ``get_actor_label()`` calls until report generation.
    """

    key: InstanceGroupKey
    actors: List[unreal.StaticMeshActor] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.actors)

    def get_labels(self, limit: int | None = None) -> List[str]:
        """Lazily resolve actor labels. Pass ``limit`` to cap O(N) cost."""
        items = self.actors[:limit] if limit is not None else self.actors
        return [a.get_actor_label() for a in items]


@dataclass
class InstanceDetectionReport:
    total_actors_scanned: int
    static_mesh_actors: int
    skipped_no_mesh: int
    skipped_no_component: int  # SMC None or RootComponent None
    skipped_non_static: int  # mobility != STATIC
    groups: List[InstanceGroup]  # sorted by count desc, includes singletons
    threshold: int
    material_slot_mismatch_count: int = 0  # all mismatches, not just the first 5 logged

    @property
    def candidate_groups(self) -> List[InstanceGroup]:
        """threshold 이상 그룹만 반환 (ISM 변환 유력 후보)."""
        return [g for g in self.groups if g.count >= self.threshold]

    @property
    def estimated_drawcall_reduction(self) -> int:
        """ISM 변환 시 예상 draw call 감소량 (추정치).

        공식: ``sum((count - 1) * num_materials for candidates)``.

        주의: Nanite / frustum culling / material complexity 제외한
        러프 estimate. 실제 GPU 측정값과 다를 수 있음.
        """
        return sum(
            (g.count - 1) * len(g.key.materials) for g in self.candidate_groups
        )


# ─── UE API isolation layer ─────────────────────────────────────────
# Future UE version bumps (5.6+) touch only this block.


def _is_static_mesh_actor(actor) -> bool:
    return isinstance(actor, unreal.StaticMeshActor)


def _get_static_mesh_component(actor):
    return actor.static_mesh_component


def _get_root_component(actor):
    return actor.root_component


def _get_static_mesh(smc):
    return smc.static_mesh


def _get_mobility(rc) -> "unreal.ComponentMobility":
    return rc.mobility


def _mobility_name(mobility) -> str:
    return mobility.name


def _is_static(mobility) -> bool:
    return mobility == unreal.ComponentMobility.STATIC


def _get_override_material_paths(smc) -> Tuple[str, ...]:
    """Per-slot material via ``get_material`` (override auto-fallback).

    ``get_material(i)`` returns the per-component override if set,
    otherwise falls back to the mesh asset's default material. Two
    actors with identical meshes and no overrides therefore produce
    identical tuples — exactly the equivalence we want for ISM grouping.
    """
    num_mats = smc.get_num_materials()
    paths: List[str] = []
    for i in range(num_mats):
        mat = smc.get_material(i)
        paths.append(mat.get_path_name() if mat else "None")
    return tuple(paths)


def _get_num_sections(sm) -> int:
    return sm.get_num_sections(0)


def _mesh_path(sm) -> str:
    return sm.get_path_name()


# ─── Public API ─────────────────────────────────────────────────────


def detect_instance_groups(
    actors: list,
    threshold: int = 10,
    should_cancel: Callable[[], bool] = lambda: False,
    on_progress: Callable[[], None] = lambda: None,
) -> InstanceDetectionReport:
    """Walk ``actors``, group by ``(mesh, materials, mobility)``. Dry-run.

    Args:
        actors: output of ``EditorActorSubsystem.get_all_level_actors()``.
        threshold: cut-off for ``candidate_groups`` property. ``groups``
            still contains every group regardless of size.
        should_cancel: polled once per iteration. True → break and return
            partial results. The caller is expected to capture any
            cancel-state externally (e.g. nonlocal flag in a closure);
            this function does not track a ``cancelled`` field.
        on_progress: invoked exactly once per actor iteration, including
            skipped actors (non-SMA, non-static, no-mesh, no-component)
            so the caller's progress bar advances uniformly. Only the
            cancelled iteration forgoes the tick.

    Notes:
        - Material slot mismatch (``smc.get_num_materials()`` vs
          ``sm.get_num_sections(0)``) is always tallied into
          ``material_slot_mismatch_count``; ``unreal.log_warning`` fires
          for at most the first 5 occurrences (log-spam cap, detection
          count unaffected).
        - Groups are sorted by count desc, singletons included.
    """
    groups: dict[InstanceGroupKey, InstanceGroup] = {}
    total = 0
    static_mesh_actors = 0
    skipped_no_mesh = 0
    skipped_no_component = 0
    skipped_non_static = 0
    mismatch_count = 0
    mismatch_warnings_logged = 0

    for actor in actors:
        if should_cancel():
            break

        total += 1

        if not _is_static_mesh_actor(actor):
            on_progress()
            continue

        static_mesh_actors += 1

        smc = _get_static_mesh_component(actor)
        rc = _get_root_component(actor)
        if smc is None or rc is None:
            skipped_no_component += 1
            on_progress()
            continue

        sm = _get_static_mesh(smc)
        if sm is None:
            skipped_no_mesh += 1
            on_progress()
            continue

        mobility = _get_mobility(rc)
        if not _is_static(mobility):
            skipped_non_static += 1
            on_progress()
            continue

        materials = _get_override_material_paths(smc)

        section_count = _get_num_sections(sm)
        if len(materials) != section_count:
            mismatch_count += 1
            if mismatch_warnings_logged < _MATERIAL_MISMATCH_WARNING_CAP:
                unreal.log_warning(
                    f"[F3] Material slot mismatch on "
                    f"'{actor.get_actor_label()}': "
                    f"{len(materials)} slots vs {section_count} sections "
                    f"(mesh: {_mesh_path(sm)}). Continuing."
                )
                mismatch_warnings_logged += 1

        key = InstanceGroupKey(
            mesh_path=_mesh_path(sm),
            materials=materials,
            mobility_name=_mobility_name(mobility),
        )
        groups.setdefault(key, InstanceGroup(key=key)).actors.append(actor)

        on_progress()

    sorted_groups = sorted(groups.values(), key=lambda g: g.count, reverse=True)
    return InstanceDetectionReport(
        total_actors_scanned=total,
        static_mesh_actors=static_mesh_actors,
        skipped_no_mesh=skipped_no_mesh,
        skipped_no_component=skipped_no_component,
        skipped_non_static=skipped_non_static,
        groups=sorted_groups,
        threshold=threshold,
        material_slot_mismatch_count=mismatch_count,
    )
