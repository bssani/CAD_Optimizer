"""Integrated report — F7.

Phase 1 산출물 통합 markdown 리포트 생성기.

설계 원칙:
- ``unreal`` 의존 0 — 순수 Python + stdlib만. 단위 테스트 / Glean / CI 등
  UE runtime 외 환경에서도 동작 가능 (F-pattern: F5 nx_naming.py와 동일).
- F2/F3/F4 in-memory dataclass를 입력으로 받음 (CSV 재파싱 X).
- F4 ``SmallPartMeasurement``는 F6 ``override_status`` /
  ``material_count`` / ``material_path_top1`` 포함. F5 ``nx_category``는
  measurement field가 아니라 ``classify_measurements()`` 결과로 별도
  list. F7은 두 입력을 zip으로 결합하여 cross-tab 계산.
- F6 inventory CSV는 per-material asset (per-actor 아님). actor join
  대상이 아니라 markdown 링크 박제용으로만 경로를 받음.
- 산출물은 markdown 문자열 1개. caller (panel.py)가 디스크에 씀.
- 별도 per-actor join CSV 산출물 없음 (F4 CSV가 이미 통합 형태).

박제 reference:
- ``docs/measurements/f4_c1yc_2_mcm.md`` (Section 7 baseline 형식)
- ``docs/measurements/f5_nx_distribution_c1yc_2_mcm.md`` (Section 7 baseline + zone 라벨)
- ``docs/concepts/material_analysis_c1yc_2_mcm.md`` (F6 override_status 3-value enum + category)
- ``docs/concepts/nx_naming_patterns.md``
- ``docs/phase2_backlog.md``

박제 zone 기준 (F5):
- UNCATEGORIZED 비율 <10% → green / 10-30% → yellow / >30% → red
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from cad_optimizer.material_inventory import (
    HAS_OVERRIDE,
    MATERIAL_CATEGORY_ORDER,
    NO_SLOT,
    SLOT_EMPTY,
    _parse_category,
)
from cad_optimizer.nx_naming import (
    NX_CATEGORY_ORDER,
    classify_measurements,
)

if TYPE_CHECKING:
    # Forward references — 런타임 import 회피 (panel.py에서 dataclass 객체를
    # 그대로 넘김. 실제 import 비용 없음).
    from cad_optimizer.instance_detector import InstanceDetectionReport
    from cad_optimizer.small_part_detector import SmallPartDetectionReport
    from cad_optimizer.stats import MeshStatsReport


# ─── Vehicle metadata ───────────────────────────────────────────────


@dataclass
class VehicleMeta:
    """Markdown header에 박힐 차량 / 측정 메타 정보.

    panel.py가 환경에서 수집해 채워서 build_report에 넘김.
    """

    vehicle_code: str = ""           # e.g. "C1YC_2_MCM"
    level_name: str = ""             # e.g. "L_C1YC_2_MCM"
    plugin_commit: str = ""          # e.g. "188a370"
    measured_at: Optional[datetime] = None  # report 생성 시각
    threshold_cm: float = 1.0        # F4 threshold 기록 (Tiny/Small/Medium 무엇으로 측정됐는지)


# ─── Public API ─────────────────────────────────────────────────────


def build_report(
    f2_stats: "MeshStatsReport",
    f3_stats: "InstanceDetectionReport",
    f4_report: "SmallPartDetectionReport",
    vehicle_meta: VehicleMeta,
    f4_csv_path: str = "",
    f6_inventory_csv_path: str = "",
    f3_csv_path: str = "",
) -> str:
    """Phase 1 산출물 통합 markdown 리포트 생성.

    Args:
        f2_stats: F2 (MeshStatsReport).
        f3_stats: F3 (InstanceDetectionReport).
        f4_report: F4 (SmallPartDetectionReport) — F5 nx_category + F6
            override_status / material_count / material_path_top1 모두
            포함. cross-tab의 단일 소스.
        vehicle_meta: 차량 / 측정 메타.
        f4_csv_path: markdown § "관련 산출물"에 박제할 F4 CSV 경로
            (per-actor 데이터는 이 파일이 master).
        f6_inventory_csv_path: markdown § "관련 산출물"에 박제할 F6
            inventory CSV 경로 (per-material asset).
        f3_csv_path: markdown § "관련 산출물"에 박제할 F3 CSV 경로
            (instance detection per-group).

    Returns:
        Markdown 문자열. caller가 디스크에 씀.
    """
    measurements = f4_report.measurements
    categories = classify_measurements(measurements)
    threshold = f4_report.threshold_cm  # 실제 측정 시 사용된 threshold (truth)

    title = f"# F7 Integrated Report — {vehicle_meta.vehicle_code or '(vehicle 미지정)'}"
    measured_str = (
        vehicle_meta.measured_at.strftime("%Y-%m-%d")
        if vehicle_meta.measured_at
        else "(미기록)"
    )
    header_line = (
        f"> **측정일**: {measured_str}  ·  "
        f"**Plugin commit**: `{vehicle_meta.plugin_commit or '(미지정)'}`"
    )

    sections: List[str] = [
        title,
        header_line,
        _render_section_overview(vehicle_meta),
        _render_section_f2(f2_stats),
        _render_section_f3(f3_stats),
        _render_section_f4(f4_report),
        _render_section_f5(measurements, categories),
        _render_section_f6(measurements, categories),
        _render_section_crosstab_f5(measurements, categories, threshold),
        _render_section_crosstab_f6(measurements, categories),
        _render_section_f8_placeholder(),
        _render_section_baseline(
            f2_stats, f3_stats, f4_report, measurements, categories
        ),
        _render_section_artifacts(f4_csv_path, f6_inventory_csv_path, f3_csv_path),
    ]

    return "\n\n".join(sections) + "\n"


# ─── Private section renderers ──────────────────────────────────────


def _h(level: int, text: str) -> str:
    """Markdown heading helper."""
    return f"{'#' * level} {text}"


def _render_section_overview(vm: "VehicleMeta") -> str:
    measured_at = (
        vm.measured_at.strftime("%Y-%m-%d %H:%M:%S")
        if vm.measured_at
        else "(미기록)"
    )
    return "\n".join([
        _h(2, "1. 측정 개요"),
        "",
        "| 항목 | 값 |",
        "|------|-----|",
        f"| 차량 코드 | `{vm.vehicle_code}` |",
        f"| 레벨명 | `{vm.level_name}` |",
        f"| 측정일 | {measured_at} |",
        f"| Plugin commit | `{vm.plugin_commit}` |",
        f"| F4 threshold | {vm.threshold_cm:.2f} cm |",
    ])


def _render_section_f2(s: "MeshStatsReport") -> str:
    return "\n".join([
        _h(2, "2. F2 — Mesh Stats"),
        "",
        "| 항목 | 값 |",
        "|------|-----|",
        f"| StaticMeshActor 수 | {s.actor_count:,} |",
        f"| Unique static meshes | {s.unique_static_meshes:,} |",
        f"| Total triangles | {s.total_triangles:,} |",
        f"| Total vertices | {s.total_vertices:,} |",
        f"| Material sections (potential draw calls) | {s.total_primitives:,} |",
        f"| Total material slots (mesh-level sum) | {s.total_material_slots:,} |",
        f"| Unique materials (mesh-level) | {s.unique_materials:,} |",
        f"| Nanite-enabled actors | {s.nanite_enabled_actors:,} / {s.actor_count:,} |",
    ])


def _render_section_f3(s: "InstanceDetectionReport") -> str:
    duplicate_groups = sum(1 for g in s.groups if g.count > 1)
    top10 = s.groups[:10]

    lines = [
        _h(2, "3. F3 — Instance Detection"),
        "",
        f"- Total groups (unique mesh + materials + mobility): **{len(s.groups):,}**",
        f"- Duplicate groups (count > 1): **{duplicate_groups:,}**",
        f"- Candidate groups (count ≥ {s.threshold}): **{len(s.candidate_groups):,}**",
        f"- Est. drawcall reduction (ISM 변환 시): **{s.estimated_drawcall_reduction:,}** (추정치)",
        "",
        "### Top 10 most-instanced groups",
        "",
        "| Rank | Count | Mesh path | Mobility |",
        "|------|-------|-----------|----------|",
    ]
    for rank, g in enumerate(top10, start=1):
        lines.append(
            f"| {rank} | {g.count:,} | `{g.key.mesh_path}` | {g.key.mobility_name} |"
        )
    return "\n".join(lines)


def _render_section_f4(s: "SmallPartDetectionReport") -> str:
    measured = len(s.measurements)
    sim = s.simulate_thresholds([0.5, 1.0, 5.0])
    sim_dict = {round(t, 2): cnt for t, cnt in sim}
    pct = s.diagonal_percentiles

    lines = [
        _h(2, "4. F4 — Small Parts"),
        "",
        f"- Total measured: **{measured:,}**",
        f"- Skipped: {s.skipped_no_root} no-root, {s.skipped_no_mesh} no-mesh, {s.skipped_zero_bbox} zero-bbox",
        f"- Root-level (no attach parent, measured): {s.skipped_no_attach_parent}",
        "",
    ]

    if pct:
        lines.extend([
            "### Diagonal 분포",
            "",
            "| Percentile | Value (cm) |",
            "|-----------|------------|",
            f"| P10 | {pct['p10']:.2f} |",
            f"| P50 | {pct['p50']:.2f} |",
            f"| P90 | {pct['p90']:.2f} |",
            "",
        ])
    else:
        lines.append("Diagonal 분포: (no measurements)")
        lines.append("")

    lines.extend([
        "### Threshold preset 카운트",
        "",
        "| Threshold | Small parts |",
        "|-----------|-------------|",
        f"| 0.5 cm (Tiny)   | {sim_dict.get(0.5, 0):,} |",
        f"| 1.0 cm (Small)  | {sim_dict.get(1.0, 0):,} |",
        f"| 5.0 cm (Medium) | {sim_dict.get(5.0, 0):,} |",
        "",
        "### Smallest 10 (by diagonal)",
        "",
        "| Rank | Diagonal | Parent (immediate attach parent) | Mobility | parent_leaf_count |",
        "|------|----------|----------------------------------|----------|-------------------|",
    ])
    smallest = s.measurements[:10]
    if not smallest:
        lines.append("| — | — | (no measurements) | — | — |")
    else:
        for rank, m in enumerate(smallest, start=1):
            parent = m.parent_part_label or "<root>"
            lines.append(
                f"| {rank} | {m.bbox_diagonal_cm:.2f} cm | "
                f"`{parent}` | {m.mobility_name} | {m.parent_leaf_count} |"
            )
    return "\n".join(lines)


def _zone_label(uncat_pct: float) -> str:
    """F5 박제 기준: <10% 🟢 green / 10-30% 🟡 yellow / >30% 🔴 red."""
    if uncat_pct < 10.0:
        return "🟢 green"
    if uncat_pct <= 30.0:
        return "🟡 yellow"
    return "🔴 red"


def _render_section_f5(measurements: list, categories: List[str]) -> str:
    cat_counts: Counter = Counter(categories)
    total = len(measurements) or 1

    lines = [
        _h(2, "5. F5 — NX Category Distribution"),
        "",
        "| Category | Count | % |",
        "|----------|-------|---|",
    ]
    for cat in NX_CATEGORY_ORDER:
        cnt = cat_counts.get(cat, 0)
        pct = cnt / total * 100.0
        lines.append(f"| {cat} | {cnt:,} | {pct:.2f}% |")
    lines.append(
        f"| **Total** | **{len(measurements):,}** | **100.00%** |"
    )

    uncat_pct = cat_counts.get("UNCATEGORIZED", 0) / total * 100.0
    zone = _zone_label(uncat_pct)
    lines.extend([
        "",
        f"**UNCATEGORIZED zone**: {zone} ({uncat_pct:.2f}%)",
        "",
        "기준: <10% 🟢 green / 10-30% 🟡 yellow / >30% 🔴 red. "
        "박제: `docs/concepts/nx_naming_patterns.md`",
    ])
    return "\n".join(lines)


def _render_section_f6(measurements: list, categories: List[str]) -> str:
    no_slot = sum(1 for m in measurements if m.override_status == NO_SLOT)
    slot_empty = sum(1 for m in measurements if m.override_status == SLOT_EMPTY)
    has_override = sum(1 for m in measurements if m.override_status == HAS_OVERRIDE)
    total = len(measurements) or 1

    # Per-actor primary slot (material_path_top1)으로 빈도 카운트 — primary slot only.
    # 전체 inventory (multi-slot, asset-level)는 § 11 inventory CSV 참조.
    mat_counter: Counter = Counter(
        m.material_path_top1 for m in measurements if m.material_path_top1
    )
    unique_mats = len(mat_counter)

    cat_counter: Counter = Counter(
        _parse_category(p) for p in mat_counter.keys()
    )

    lines = [
        _h(2, "6. F6 — Material Inventory"),
        "",
        f"- Total unique materials (per-actor primary slot): **{unique_mats}**",
        "  - 본 카운트는 actor의 slot 0 기준. 전체 inventory (multi-slot, "
        "asset-level)는 § 11 inventory CSV 참조.",
        "",
        "### Override status 분포 (3-value enum)",
        "",
        "| Status | Count | % | 의미 |",
        "|--------|-------|---|------|",
        f"| `no_slot` | {no_slot:,} | {no_slot / total * 100.0:.2f}% | "
        f"`smc.get_num_materials() == 0` |",
        f"| `slot_empty` | {slot_empty:,} | {slot_empty / total * 100.0:.2f}% | "
        f"slot 존재, asset None → mesh default fallback (typical Datasmith CAD) |",
        f"| `has_override` | {has_override:,} | "
        f"{has_override / total * 100.0:.2f}% | slot + asset 둘 다 |",
        "",
        "### Top 10 materials (by per-actor primary slot usage)",
        "",
        "| Rank | Path | Usage |",
        "|------|------|-------|",
    ]
    for rank, (path, cnt) in enumerate(mat_counter.most_common(10), start=1):
        lines.append(f"| {rank} | `{path}` | {cnt:,} |")
    if unique_mats == 0:
        lines.append("| — | (no materials found) | — |")

    cat_total = unique_mats or 1
    lines.extend([
        "",
        "### Material category breakdown (unique assets)",
        "",
        f"| Category | Unique materials | % of {unique_mats} |",
        "|----------|------------------|------|",
    ])
    for cat in MATERIAL_CATEGORY_ORDER:
        cnt = cat_counter.get(cat, 0)
        pct = cnt / cat_total * 100.0
        lines.append(f"| {cat} | {cnt} | {pct:.2f}% |")

    lines.extend([
        "",
        "박제 (3-value enum 정의 + 카테고리 regex): "
        "`docs/concepts/material_analysis_c1yc_2_mcm.md` § 8.",
    ])
    return "\n".join(lines)


def _render_section_crosstab_f5(
    measurements: list,
    categories: List[str],
    threshold_cm: float,
) -> str:
    ct = _crosstab_nx_x_small(measurements, categories, threshold_cm)
    lines = [
        _h(2, f"7. F4 × F5 Cross-tab — nx_category × is_small (Tiny @ {threshold_cm:.1f} cm)"),
        "",
        "| nx_category | small | not small | total | % small |",
        "|-------------|-------|-----------|-------|---------|",
    ]
    for cat in NX_CATEGORY_ORDER:
        b = ct[cat]
        cat_total = b["small"] + b["not_small"]
        pct = (b["small"] / cat_total * 100.0) if cat_total else 0.0
        lines.append(
            f"| {cat} | {b['small']:,} | {b['not_small']:,} | "
            f"{cat_total:,} | {pct:.2f}% |"
        )
    return "\n".join(lines)


def _render_section_crosstab_f6(
    measurements: list,
    categories: List[str],
) -> str:
    ct = _crosstab_nx_x_override(measurements, categories)
    lines = [
        _h(2, "8. F4 × F6 Cross-tab — nx_category × override_status"),
        "",
        "| nx_category | no_slot | slot_empty | has_override | total |",
        "|-------------|---------|------------|--------------|-------|",
    ]
    for cat in NX_CATEGORY_ORDER:
        b = ct[cat]
        cat_total = b[NO_SLOT] + b[SLOT_EMPTY] + b[HAS_OVERRIDE]
        lines.append(
            f"| {cat} | {b[NO_SLOT]:,} | {b[SLOT_EMPTY]:,} | "
            f"{b[HAS_OVERRIDE]:,} | {cat_total:,} |"
        )
    lines.extend([
        "",
        "**해석 가설**: `slot_empty` 비율이 높은 카테고리는 mesh default "
        "fallback에 의존. Phase 2 ISM/Nanite 작업 시 우선 검토 후보.",
    ])
    return "\n".join(lines)


def _render_section_f8_placeholder() -> str:
    return "\n".join([
        _h(2, "9. F8 — Metadata Tags"),
        "",
        "<!-- F8 placeholder, populated post-F8 implementation -->",
    ])


def _render_section_baseline(
    f2_stats: "MeshStatsReport",
    f3_stats: "InstanceDetectionReport",
    f4_report: "SmallPartDetectionReport",
    measurements: list,
    categories: List[str],
) -> str:
    cat_counts: Counter = Counter(categories)
    total = len(measurements)
    no_slot = sum(1 for m in measurements if m.override_status == NO_SLOT)
    slot_empty = sum(1 for m in measurements if m.override_status == SLOT_EMPTY)
    has_override = sum(1 for m in measurements if m.override_status == HAS_OVERRIDE)
    sim = f4_report.simulate_thresholds([0.5, 1.0, 5.0])
    sim_dict = {round(t, 2): cnt for t, cnt in sim}
    pct = f4_report.diagonal_percentiles or {"p10": 0.0, "p50": 0.0, "p90": 0.0}
    unique_primary_mats = len({
        m.material_path_top1 for m in measurements if m.material_path_top1
    })

    lines = [
        _h(2, "10. 다음 차량 비교용 baseline"),
        "",
        "```",
        "# F2",
        f"F2_TOTAL_ACTORS = {f2_stats.actor_count}",
        f"F2_UNIQUE_MESHES = {f2_stats.unique_static_meshes}",
        f"F2_TOTAL_TRIANGLES = {f2_stats.total_triangles}",
        f"F2_TOTAL_VERTICES = {f2_stats.total_vertices}",
        f"F2_NANITE_ENABLED = {f2_stats.nanite_enabled_actors}",
        "",
        "# F3",
        f"F3_TOTAL_GROUPS = {len(f3_stats.groups)}",
        f"F3_DUPLICATE_GROUPS = {sum(1 for g in f3_stats.groups if g.count > 1)}",
        f"F3_CANDIDATE_GROUPS = {len(f3_stats.candidate_groups)}",
        f"F3_EST_DRAWCALL_REDUCTION = {f3_stats.estimated_drawcall_reduction}",
        "",
        "# F4",
        f"F4_TOTAL_MEASURED = {total}",
        f"F4_DIAG_P10_CM = {pct['p10']:.3f}",
        f"F4_DIAG_P50_CM = {pct['p50']:.3f}",
        f"F4_DIAG_P90_CM = {pct['p90']:.3f}",
        f"F4_SMALL_AT_0_5_CM = {sim_dict.get(0.5, 0)}",
        f"F4_SMALL_AT_1_0_CM = {sim_dict.get(1.0, 0)}",
        f"F4_SMALL_AT_5_0_CM = {sim_dict.get(5.0, 0)}",
        "",
        "# F5",
    ]
    for cat in NX_CATEGORY_ORDER:
        lines.append(f"F5_{cat} = {cat_counts.get(cat, 0)}")
    safe_total = total or 1
    lines.append(
        f"F5_UNCAT_PCT = "
        f"{cat_counts.get('UNCATEGORIZED', 0) / safe_total * 100.0:.2f}"
    )
    lines.extend([
        "",
        "# F6 (per-actor primary slot)",
        f"F6_NO_SLOT = {no_slot}",
        f"F6_SLOT_EMPTY = {slot_empty}",
        f"F6_HAS_OVERRIDE = {has_override}",
        f"F6_UNIQUE_PRIMARY_MATERIALS = {unique_primary_mats}",
        "```",
    ])
    return "\n".join(lines)


def _render_section_artifacts(f4_csv: str, f6_csv: str, f3_csv: str) -> str:
    f4_line = f"  `{f4_csv}`" if f4_csv else "  (경로 미제공)"
    f6_line = f"  `{f6_csv}`" if f6_csv else "  (경로 미제공)"
    f3_line = f"  `{f3_csv}`" if f3_csv else "  (경로 미제공)"
    return "\n".join([
        _h(2, "11. 관련 산출물"),
        "",
        "**Primary**: 본 markdown (이 파일).",
        "",
        "**Supporting CSVs** (동일 측정 시점 박제):",
        "- F4 per-actor CSV (master per-actor data — F5 nx_category + "
        "F6 material 통합):",
        f4_line,
        "- F6 inventory CSV (per-material asset, F4 CSV에 없는 multi-slot/"
        "asset-level inventory):",
        f6_line,
        "- F3 instance detection CSV (ISM 변환 후보 per-group):",
        f3_line,
        "",
        "### 박제 reference",
        "",
        "- `docs/measurements/f4_c1yc_2_mcm.md` — F4 baseline 형식",
        "- `docs/measurements/f5_nx_distribution_c1yc_2_mcm.md` — F5 분포 + zone",
        "- `docs/concepts/material_analysis_c1yc_2_mcm.md` — F6 3-value enum 정의",
        "- `docs/concepts/nx_naming_patterns.md` — V2 regex 출처",
        "- `docs/phase2_backlog.md` — Phase 2 미결정 항목",
    ])


# ─── Cross-tab 계산 ─────────────────────────────────────────────────


def _crosstab_nx_x_small(
    measurements: list,
    categories: List[str],
    threshold_cm: float,
) -> "OrderedDict[str, Dict[str, int]]":
    """nx_category × is_small 교차 카운트.

    Args:
        measurements: ``SmallPartMeasurement`` list (``bbox_diagonal_cm``
            field 사용).
        categories: ``classify_measurements(measurements)`` 결과 (parallel list).
        threshold_cm: ``bbox_diagonal_cm < threshold_cm`` 이면 small.

    Returns:
        OrderedDict[nx_category, {"small": int, "not_small": int}]
        (NX_CATEGORY_ORDER 순서 유지, 각 카테고리는 항상 존재. 카운트 0
        가능).
    """
    result: "OrderedDict[str, Dict[str, int]]" = OrderedDict(
        (cat, {"small": 0, "not_small": 0}) for cat in NX_CATEGORY_ORDER
    )
    for m, cat in zip(measurements, categories):
        bucket = result.get(cat)
        if bucket is None:
            # NX_CATEGORY_ORDER 외 값 — defensive (정상 흐름에선 발생 X)
            continue
        if m.bbox_diagonal_cm < threshold_cm:
            bucket["small"] += 1
        else:
            bucket["not_small"] += 1
    return result


def _crosstab_nx_x_override(
    measurements: list,
    categories: List[str],
) -> "OrderedDict[str, Dict[str, int]]":
    """nx_category × override_status 교차 카운트.

    Args:
        measurements: ``SmallPartMeasurement`` list (``override_status``
            field 사용 — F6 fix 후 3-value enum).
        categories: ``classify_measurements(measurements)`` 결과 (parallel list).

    Returns:
        OrderedDict[nx_category, {NO_SLOT: int, SLOT_EMPTY: int, HAS_OVERRIDE: int}]
        (NX_CATEGORY_ORDER 순서 유지).
    """
    result: "OrderedDict[str, Dict[str, int]]" = OrderedDict(
        (cat, {NO_SLOT: 0, SLOT_EMPTY: 0, HAS_OVERRIDE: 0})
        for cat in NX_CATEGORY_ORDER
    )
    for m, cat in zip(measurements, categories):
        bucket = result.get(cat)
        if bucket is None:
            continue
        status = m.override_status
        if status in bucket:
            bucket[status] += 1
        # 알 수 없는 status는 silently skip (regression 가드)
    return result
