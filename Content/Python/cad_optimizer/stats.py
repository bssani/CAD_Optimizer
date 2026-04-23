"""Mesh statistics collection — F2.

Pure module: only `unreal` + stdlib. No UI / SlowIter coupling, so
this can be driven from tests, F7 reporters, or alternative front-ends
without dragging UMG widget code in.

All direct unreal.* calls live in the ``_get_*`` / ``_is_*`` helpers
below; future UE version bumps touch exactly that block.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional, Set

import unreal


@dataclass
class MeshStatsReport:
    """레벨 진단 결과.

    Notes:
        - ``total_primitives``는 내부 명명 (gltf 호환). UI 라벨은
          "Material Sections (Potential Draw Calls)".
          Nanite/instancing 미반영 naive upper bound.
        - ``cancelled=True`` 시 partial 결과. UI에서 반드시 시각적 표시.
        - ``skipped_hidden_count``는 ``skip_hidden=True``일 때만 의미 있음.
    """

    actor_count: int = 0
    total_triangles: int = 0
    total_vertices: int = 0
    total_primitives: int = 0
    total_material_slots: int = 0
    unique_materials: int = 0
    unique_static_meshes: int = 0
    nanite_enabled_actors: int = 0
    skipped_hidden_count: int = 0
    scanned_at: Optional[datetime] = None
    cancelled: bool = False

    def to_dict(self) -> dict:
        """F7 리포트용 JSON 직렬화 hook."""
        d = asdict(self)
        if self.scanned_at:
            d["scanned_at"] = self.scanned_at.isoformat()
        return d


# ─── UE API isolation layer ─────────────────────────────────────────
# Future UE version bumps (5.6+) only touch this block.


def _is_static_mesh_actor(actor) -> bool:
    return isinstance(actor, unreal.StaticMeshActor)


def _is_hidden(actor) -> bool:
    return bool(actor.is_hidden_ed())


def _get_static_mesh(actor):
    smc = actor.static_mesh_component
    if smc is None:
        return None
    return smc.static_mesh


def _get_triangles(sm, lod: int = 0) -> int:
    return sm.get_num_triangles(lod)


def _get_sections(sm, lod: int = 0) -> int:
    return sm.get_num_sections(lod)


def _get_vertices(sm, lod: int = 0) -> int:
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    return smes.get_number_verts(sm, lod)


def _is_nanite_enabled(sm) -> bool:
    return bool(sm.get_editor_property("nanite_settings").enabled)


def _mesh_path(sm) -> str:
    return sm.get_path_name()


def _iter_material_paths(sm) -> Iterable[Optional[str]]:
    """Yield one entry per material slot. None for unassigned slots."""
    for slot in sm.static_materials:
        mat = slot.material_interface
        yield None if mat is None else mat.get_path_name()


# ─── Public API ─────────────────────────────────────────────────────


def collect_mesh_stats(
    actors: Iterable,
    should_cancel: Callable[[], bool],
    on_progress: Callable[[], None],
    skip_hidden: bool = False,
) -> MeshStatsReport:
    """Walk ``actors`` and aggregate LOD0 mesh stats. Cancellable.

    Contract with caller:
        - StaticMeshActor filter lives inside this function.
        - Per actor: ``should_cancel()`` first → process → ``on_progress()``.
        - ``on_progress()`` is called even when an actor is skipped
          (non-SMA, hidden+skip, component/mesh None) so the caller's
          progress bar advances uniformly.
        - Cancel → break, set ``cancelled=True``, return partial report.
          No exception raised.
    """
    report = MeshStatsReport()
    unique_mats: Set[str] = set()
    unique_meshes: Set[str] = set()

    for actor in actors:
        if should_cancel():
            report.cancelled = True
            break

        if not _is_static_mesh_actor(actor):
            on_progress()
            continue

        if skip_hidden and _is_hidden(actor):
            report.skipped_hidden_count += 1
            on_progress()
            continue

        sm = _get_static_mesh(actor)
        if sm is None:
            on_progress()
            continue

        report.actor_count += 1
        report.total_triangles += _get_triangles(sm, 0)
        report.total_vertices += _get_vertices(sm, 0)
        report.total_primitives += _get_sections(sm, 0)

        slot_count = 0
        for mat_path in _iter_material_paths(sm):
            slot_count += 1
            if mat_path is not None:
                unique_mats.add(mat_path)
        report.total_material_slots += slot_count

        unique_meshes.add(_mesh_path(sm))

        if _is_nanite_enabled(sm):
            report.nanite_enabled_actors += 1

        on_progress()

    report.unique_materials = len(unique_mats)
    report.unique_static_meshes = len(unique_meshes)
    report.scanned_at = datetime.now()
    return report
