"""Material inventory — F6.

Two-angle measurement of materials in the level:

1. **Per-actor status** — for each StaticMeshActor:
   - material_count: smc.get_num_materials() returns
   - override_status: 3-value enum — no_slot | slot_empty | has_override
     (실차 검증 기반, 박제 docs/concepts/material_analysis_c1yc_2_mcm.md
     Section 8)
   - material_path_top1: rendering material — override or mesh default
     fallback. Empty only when both component override and mesh default
     are None.

2. **Asset inventory** — for each unique material path used in the level:
   - usage_via_override: HAS_OVERRIDE actors가 명시 binding한 횟수
   - usage_via_default: SLOT_EMPTY/NO_SLOT actors가 mesh default로 fallback한 횟수
   - category: parsed from path (CarPaint/Metal/.../Features/UNKNOWN)
   - is_instance: MI_* prefix vs M_* base

Notes:
    - Datasmith CAD import는 component slot을 보통 만들지만 asset binding은
      mesh default에 위임하는 경우가 많음 (~58.9% slot_empty in C1YC_2_MCM).
      이건 결함이 아니라 정상 fallback 상태.
    - Mesh default fallback path는 ``sm.static_materials[0].material_interface``
      (F2 검증된 API) 사용. ``sm.get_material(0)``은 UE 5.5 Python에서
      미검증이라 회피. 박제: docs/lessons_learned/api_verification_first.md.
    - Inventory는 shallow: 어떤 material이 어떻게 쓰이는가만. Material asset
      속성 (텍스처, 파라미터) 비교는 Phase 2.
"""
from __future__ import annotations

import re
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Callable, List, Optional

import unreal


# Material asset 분류 카테고리 (canonical 순서, Output Log 안정성).
# Features는 /01_Features/ 경로 (Top 1 MI_SectionMisc 등 — 점유율 높음).
MATERIAL_CATEGORY_ORDER: List[str] = [
    "CarPaint", "Metal", "Plastic", "Glass", "Rubber", "Misc",
    "Features",
    "UNKNOWN"
]


# Override status — 3-value enum (실차 검증 기반).
# 박제: docs/concepts/material_analysis_c1yc_2_mcm.md Section 8
NO_SLOT = "no_slot"               # smc.get_num_materials() == 0
SLOT_EMPTY = "slot_empty"          # slot 존재, smc.get_material(i) returns None
                                   # → mesh default fallback (typical Datasmith CAD)
HAS_OVERRIDE = "has_override"      # slot 존재 + asset 존재


@dataclass
class PerActorMaterialStatus:
    """Per-actor material info — joined into F4 CSV row."""

    material_count: int        # smc.get_num_materials() returns
    override_status: str       # NO_SLOT | SLOT_EMPTY | HAS_OVERRIDE
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
    # 3-value enum 카운터 (박제 Section 8)
    no_slot_count: int
    slot_empty_count: int
    has_override_count: int
    assets: List[MaterialAssetEntry]  # sorted by total_usage desc

    @property
    def total_unique_materials(self) -> int:
        return len(self.assets)


# ─── Helpers ────────────────────────────────────────────────────────


def _parse_category(material_path: str) -> str:
    """Extract category from path. Priority order (실차 검증 기반):

    1. ``/02_Instance/<category>/`` — must match canonical name
    2. ``/01_Features/`` → fixed ``"Features"`` (basename 무시; Features
       디렉토리는 purpose-organized)
    3. ``/00_Material/<category>/`` (fallback) — must match canonical name
    4. anything else → ``"UNKNOWN"``
    """
    # Pattern 1: /02_Instance/<category>/
    m = re.search(r"/02_Instance/([^/]+)/", material_path)
    if m:
        cat = m.group(1)
        return cat if cat in MATERIAL_CATEGORY_ORDER else "UNKNOWN"

    # Pattern 2: /01_Features/ — fixed Features 카테고리
    if "/01_Features/" in material_path:
        return "Features"

    # Pattern 3: /00_Material/<category>/ (fallback)
    m = re.search(r"/00_Material/([^/]+)/", material_path)
    if m:
        cat = m.group(1)
        if cat in MATERIAL_CATEGORY_ORDER:
            return cat

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


def _get_mesh_default_path(smc) -> str:
    """Mesh default material path (slot 0). Empty string if unavailable.

    Uses ``sm.static_materials[0].material_interface`` (F2-verified API,
    UE 5.5 compatible). Avoids ``sm.get_material()`` which may not exist
    in this UE version (api_verification_first.md).
    """
    sm = smc.static_mesh
    if sm is None:
        return ""

    static_materials = sm.static_materials if hasattr(sm, "static_materials") else None
    if not static_materials:
        return ""

    try:
        first_static = static_materials[0]
    except (IndexError, TypeError):
        return ""

    interface = getattr(first_static, "material_interface", None)
    if interface is None:
        return ""

    return interface.get_path_name()


# ─── Per-actor status (F4 측정 시 결합 호출용) ──────────────────────


def measure_actor_material_status(actor) -> PerActorMaterialStatus:
    """Per-actor material override status (3-value enum).

    Determines one of three states:
        - NO_SLOT: ``smc.get_num_materials() == 0``
        - SLOT_EMPTY: slot exists but ``smc.get_material(0)`` returns None.
          Renders using mesh default. Typical for Datasmith CAD import
          (~58.9% in C1YC_2_MCM).
        - HAS_OVERRIDE: slot exists + asset present.

    ``material_path_top1`` always tries to populate with the effective
    rendering material:
        - HAS_OVERRIDE: ``smc.get_material(0).get_path_name()``
        - SLOT_EMPTY / NO_SLOT: mesh default fallback (sm.static_materials[0])
        - All paths None: empty string
    """
    smc = actor.static_mesh_component
    if smc is None:
        return PerActorMaterialStatus(0, NO_SLOT, "")

    n_overrides = smc.get_num_materials() if hasattr(smc, "get_num_materials") else 0

    if n_overrides == 0:
        # NO_SLOT: 슬롯 자체가 없음. mesh default 채울 수 있으면 채움.
        return PerActorMaterialStatus(0, NO_SLOT, _get_mesh_default_path(smc))

    # 슬롯 존재. 첫 번째 slot 값 확인
    first_material = smc.get_material(0)

    if first_material is None:
        # SLOT_EMPTY: 슬롯 있지만 asset None → mesh default fallback
        return PerActorMaterialStatus(
            n_overrides, SLOT_EMPTY, _get_mesh_default_path(smc)
        )

    # HAS_OVERRIDE: slot + asset 둘 다 존재
    return PerActorMaterialStatus(
        n_overrides, HAS_OVERRIDE, first_material.get_path_name()
    )


# ─── Asset inventory (F6 menu entry용) ──────────────────────────────


def build_inventory(
    actors: list,
    should_cancel: Callable[[], bool] = lambda: False,
    on_progress: Callable[[], None] = lambda: None,
) -> MaterialInventoryReport:
    """Walk all StaticMeshActors and build material asset inventory.

    Two counters per material:
        - ``usage_via_override``: HAS_OVERRIDE actor가 명시 binding한 횟수
        - ``usage_via_default``: SLOT_EMPTY/NO_SLOT actor가 mesh default로
          fallback한 횟수

    Per-actor counter (3-value enum): ``no_slot_count``, ``slot_empty_count``,
    ``has_override_count``.

    Total unique materials = ``len(assets)``. Sorted by ``total_usage`` desc.
    """
    override_usage: Counter = Counter()
    default_usage: Counter = Counter()

    total = 0
    sma_count = 0
    no_smc = 0
    no_sm = 0
    no_slot = 0
    slot_empty = 0
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

        if n_overrides == 0:
            no_slot += 1
            # NO_SLOT도 mesh default 카운트 (실차에서 0건일 가능성 큼)
            default_path = _get_mesh_default_path(smc)
            if default_path:
                default_usage[default_path] += 1
        else:
            first = smc.get_material(0)
            if first is None:
                slot_empty += 1
                # SLOT_EMPTY: mesh default fallback 카운트
                default_path = _get_mesh_default_path(smc)
                if default_path:
                    default_usage[default_path] += 1
            else:
                has_override += 1
                # HAS_OVERRIDE: 모든 slot의 override 카운트
                for i in range(n_overrides):
                    m = smc.get_material(i)
                    if m:
                        override_usage[m.get_path_name()] += 1

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
        no_slot_count=no_slot,
        slot_empty_count=slot_empty,
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
