"""Material inventory — F6.

Two-angle measurement of materials in the level:

1. **Per-actor status** — for each StaticMeshActor:
   - material_count: smc.get_material() returns (component-level)
   - override_status: "no_override" if count == 0 else "has_override"
   - material_path_top1: first override path, or mesh default fallback

2. **Asset inventory** — for each unique material path used in the level:
   - usage_count (via smc override or sm default)
   - category (parsed from path: CarPaint/Metal/Plastic/Glass/Rubber/Misc/UNKNOWN)
   - is_instance (MI_* prefix vs M_* base material)

Notes:
    - F2 measures sm.static_materials (mesh-level). F6 measures
      smc.get_material() (component-level). The two counts often differ
      — typical for Datasmith CAD import where most actors do not
      override the mesh default material. ~58.9% no_override observed
      in C1YC_2_MCM (see docs/concepts/material_analysis_c1yc_2_mcm.md).
      This is normal fallback behavior, not a defect.
    - Inventory is shallow: it identifies which materials exist and how
      they are used. Material asset properties (textures, parameters)
      are NOT compared — Phase 2 territory if duplicate detection across
      asset properties is needed.
    - Mesh default fallback path uses ``sm.static_materials[0].material_interface``
      (verified in F2 stats.py) — NOT ``sm.get_material(0)`` which is
      not confirmed in UE 5.5 Python.
"""
from __future__ import annotations

import re
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Callable, List, Optional

import unreal


# 박제: docs/concepts/material_analysis_c1yc_2_mcm.md
# Path 카테고리 추출 — /Game/00_PQDQ/00_Material/02_Instance/<category>/MI_*
_CATEGORY_PATTERN = re.compile(r"/02_Instance/([^/]+)/")

# Material asset 분류 카테고리 (canonical 순서, Output Log 안정성).
MATERIAL_CATEGORY_ORDER: List[str] = [
    "CarPaint", "Metal", "Plastic", "Glass", "Rubber", "Misc", "UNKNOWN"
]

# Override status 두 가지.
NO_OVERRIDE = "no_override"
HAS_OVERRIDE = "has_override"


@dataclass
class PerActorMaterialStatus:
    """Per-actor material info — joined into F4 CSV row.

    Caller (F4 ``detect_small_parts``) ensures parallel order with
    its measurements list; F6 stores these on the measurement itself
    via ``small_part_detector.SmallPartMeasurement`` field extension.
    """

    material_count: int        # smc.get_material(i) override count
    override_status: str       # NO_OVERRIDE | HAS_OVERRIDE
    material_path_top1: str    # primary material (override or mesh default)


@dataclass
class MaterialAssetEntry:
    """Material asset inventory row — one per unique material path."""

    material_path: str
    usage_via_override: int = 0       # smc.get_material 호출에서 카운트
    usage_via_default: int = 0        # sm default (override 없는 actor의 fallback)
    category: str = "UNKNOWN"
    is_instance: bool = False         # MI_* prefix
    is_base: bool = False             # M_* prefix (MI_와 배타적)

    @property
    def total_usage(self) -> int:
        return self.usage_via_override + self.usage_via_default


@dataclass
class MaterialInventoryReport:
    total_actors_scanned: int
    sma_count: int
    skipped_no_smc: int
    skipped_no_sm: int
    no_override_count: int          # material_count == 0
    has_override_count: int         # material_count > 0
    assets: List[MaterialAssetEntry]  # sorted by total_usage desc

    @property
    def total_unique_materials(self) -> int:
        return len(self.assets)


# ─── Helpers ────────────────────────────────────────────────────────


def _parse_category(material_path: str) -> str:
    """Extract category from path. Returns 'UNKNOWN' if no match."""
    match = _CATEGORY_PATTERN.search(material_path)
    if match:
        cat = match.group(1)
        return cat if cat in MATERIAL_CATEGORY_ORDER else "UNKNOWN"
    return "UNKNOWN"


def _classify_prefix(material_path: str) -> tuple[bool, bool]:
    """Return ``(is_instance, is_base)`` from basename prefix.

    ``MI_*``  → (True,  False)
    ``M_*``   → (False, True)   — MI_가 아닌 M_로 시작
    other    → (False, False)
    """
    basename = material_path.rsplit("/", 1)[-1].split(".")[0]
    is_instance = basename.startswith("MI_")
    is_base = basename.startswith("M_") and not basename.startswith("MI_")
    return is_instance, is_base


def _mesh_default_top_path(sm) -> str:
    """First mesh default material path via ``sm.static_materials`` (F2 verified API).

    Returns empty string if no slots or material_interface is None.
    """
    try:
        slots = sm.static_materials
    except Exception:
        return ""
    if not slots:
        return ""
    try:
        slot = slots[0]
    except (IndexError, TypeError):
        return ""
    mat = getattr(slot, "material_interface", None)
    if mat is None:
        return ""
    return mat.get_path_name()


# ─── Per-actor status (F4 측정 시 결합 호출용) ──────────────────────


def measure_actor_material_status(actor) -> PerActorMaterialStatus:
    """For one StaticMeshActor: get override count + primary path.

    Caller (small_part_detector.detect_small_parts) supplies actors that
    already passed F4's null-safety gates (smc/sm not None). This
    function still re-validates defensively.
    """
    smc = actor.static_mesh_component
    if smc is None:
        return PerActorMaterialStatus(0, NO_OVERRIDE, "")

    n_overrides = smc.get_num_materials() if hasattr(smc, "get_num_materials") else 0

    if n_overrides > 0:
        m = smc.get_material(0)
        path = m.get_path_name() if m else ""
        return PerActorMaterialStatus(n_overrides, HAS_OVERRIDE, path)

    # No override: fallback to mesh default
    sm = smc.static_mesh
    if sm is None:
        return PerActorMaterialStatus(0, NO_OVERRIDE, "")

    return PerActorMaterialStatus(0, NO_OVERRIDE, _mesh_default_top_path(sm))


# ─── Asset inventory (F6 menu entry용) ──────────────────────────────


def build_inventory(
    actors: list,
    should_cancel: Callable[[], bool] = lambda: False,
    on_progress: Callable[[], None] = lambda: None,
) -> MaterialInventoryReport:
    """Walk all StaticMeshActors and build material asset inventory.

    Two counters per material:
        - usage_via_override: counted from smc.get_material(i) iterations
        - usage_via_default: counted when actor has no override and
          falls back to sm default (mesh-level)

    Total unique materials = len(assets). Sorted by total_usage desc.
    """
    override_usage: Counter = Counter()
    default_usage: Counter = Counter()

    total = 0
    sma_count = 0
    no_smc = 0
    no_sm = 0
    no_override = 0
    has_override = 0

    for actor in actors:
        if should_cancel():
            break
        total += 1

        if not isinstance(actor, unreal.StaticMeshActor):
            on_progress()
            continue
        sma_count += 1

        smc = actor.static_mesh_component
        if smc is None:
            no_smc += 1
            on_progress()
            continue

        sm = smc.static_mesh
        if sm is None:
            no_sm += 1
            on_progress()
            continue

        n_overrides = smc.get_num_materials() if hasattr(smc, "get_num_materials") else 0

        if n_overrides > 0:
            has_override += 1
            for i in range(n_overrides):
                m = smc.get_material(i)
                if m:
                    override_usage[m.get_path_name()] += 1
        else:
            no_override += 1
            # Mesh default fallback — primary slot only (sufficient for inventory;
            # full multi-slot default tracking is Phase 2). Verified API path.
            default_path = _mesh_default_top_path(sm)
            if default_path:
                default_usage[default_path] += 1

        on_progress()

    # Build asset entries
    all_paths = set(override_usage.keys()) | set(default_usage.keys())
    assets: List[MaterialAssetEntry] = []
    for path in all_paths:
        is_inst, is_base = _classify_prefix(path)
        assets.append(MaterialAssetEntry(
            material_path=path,
            usage_via_override=override_usage[path],
            usage_via_default=default_usage[path],
            category=_parse_category(path),
            is_instance=is_inst,
            is_base=is_base,
        ))

    assets.sort(key=lambda a: a.total_usage, reverse=True)

    return MaterialInventoryReport(
        total_actors_scanned=total,
        sma_count=sma_count,
        skipped_no_smc=no_smc,
        skipped_no_sm=no_sm,
        no_override_count=no_override,
        has_override_count=has_override,
        assets=assets,
    )


# ─── 카테고리 집계 (Output Log용) ───────────────────────────────────


def category_counts(
    assets: List[MaterialAssetEntry],
) -> "OrderedDict[str, int]":
    """Count assets per category in canonical order. Empty categories
    appear with count 0 (predictable Output Log layout).
    """
    raw = Counter(a.category for a in assets)
    return OrderedDict((cat, raw.get(cat, 0)) for cat in MATERIAL_CATEGORY_ORDER)
