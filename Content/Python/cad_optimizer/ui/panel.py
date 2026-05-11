"""F2 + F3 + F4 runners + EUW glue.

F2 — ``run_scan_level`` (mesh stats diagnostic):
    - EUW button → pushes stats into the widget's ``lbl_*`` Text Blocks.
    - Tools > Scan Level → ``widget=None``, Output Log dump.

F3 — ``run_detect_instances`` (ISM candidate detection):
    - Tools > Detect Instances or EUW button → writes CSV report to
      ``{project_saved_dir}/CAD_Optimizer/instance_report_{ts}.csv``
      and logs a top-10 summary to Output Log.
    - Detection-only. Level/actors are never mutated.

F4 — ``run_detect_small_parts`` (PCVR culling candidate detection):
    - Tools > Detect Small Parts (3 presets) or EUW Custom button →
      writes CSV report to
      ``{project_saved_dir}/CAD_Optimizer/small_part_report_{ts}.csv``
      and logs a multi-threshold simulation table + smallest-10 summary.
    - Detection-only. Single entry point; Preset values come from
      ``small_part_detector.PRESETS`` so menu/EUW/CSV stay in sync.

Progress + cancel come from ``unreal.ScopedSlowTask`` directly, not
``SlowIter``, because the core modules (``stats``, ``instance_detector``,
``small_part_detector``) are callback-driven and must stay ignorant of
SlowIter. Same underlying freeze-prevention mechanism; F0 pattern preserved.

EUW Blueprint guide for the F3 entry:

    Section: "F3 Instance Detection"
      - SpinBox (int) : Threshold, default=10, min=2, max=1000
                        (variable name: ``sb_f3_threshold``)
      - Button         : "Run Detection"
          OnClicked:
            sb_f3_threshold.Value → Format Text:
              "cad_optimizer.ui.panel.run_detect_instances(threshold={0})"
            → Execute Python Command
    Reuses the Format Text pattern established in F2 (week02.md §3).

EUW Blueprint guide for the F4 entry:

    Section: "F4 Small Part Detection"
      [Quick Presets] (each button OnClicked → Execute Python directly)
      - Button: "Tiny (< 0.5 cm)"
          → "cad_optimizer.ui.panel.run_detect_small_parts(threshold_cm=0.5)"
      - Button: "Small (< 1.0 cm)"
          → "cad_optimizer.ui.panel.run_detect_small_parts(threshold_cm=1.0)"
      - Button: "Medium (< 5.0 cm)"
          → "cad_optimizer.ui.panel.run_detect_small_parts(threshold_cm=5.0)"

      [Custom]
      - SpinBox (float): "Threshold (cm)", default=1.0, min=0.01, max=100.0
                         (variable name: ``sb_f4_threshold_cm``)
      - Button: "Run Custom Detection"
          OnClicked:
            sb_f4_threshold_cm.Value → Format Text:
              "cad_optimizer.ui.panel.run_detect_small_parts(threshold_cm={0})"
            → Execute Python Command

    Preset 값 변경: ``small_part_detector.PRESETS`` 만 수정해도 menu.py는
    동기화되지만, EUW preset 버튼 hardcoded 값은 자동 동기화 X — Phase 1
    후반 일괄 naming/preset pass에서 통합 검토.
"""
from __future__ import annotations

import csv
import math
import os
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

import unreal

from cad_optimizer.instance_detector import (
    InstanceDetectionReport,
    detect_instance_groups,
)
from cad_optimizer.integrated_report import VehicleMeta, build_report
from cad_optimizer.material_inventory import (
    HAS_OVERRIDE,
    MATERIAL_CATEGORY_ORDER,
    MaterialInventoryReport,
    NO_SLOT,
    SLOT_EMPTY,
    build_inventory,
)
from cad_optimizer.material_inventory import category_counts as material_category_counts
from cad_optimizer.metadata_tagger import (
    TIER_KEEP,
    TIER_ORDER,
    TagApplicationResult,
    apply_tags_to_level,
)
from cad_optimizer.nx_naming import (
    NX_CATEGORY_ORDER,
    UNCATEGORIZED,
    category_counts,
    classify_measurements,
)
from cad_optimizer.small_part_detector import (
    PRESETS,
    SIMULATION_THRESHOLDS_CM,
    SmallPartDetectionReport,
    detect_small_parts,
)
from cad_optimizer.stats import MeshStatsReport, collect_mesh_stats


_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def run_scan_level(
    widget: Optional["unreal.EditorUtilityWidget"] = None,
    skip_hidden: bool = False,
) -> MeshStatsReport:
    """F2 entry point.

    Args:
        widget: EUW instance that owns ``lbl_*`` Text Blocks.
            When None, results are logged instead of pushed to UI.
        skip_hidden: Mirrors the EUW "Skip hidden actors" checkbox.

    Returns:
        MeshStatsReport (caller usable directly even when widget is set —
        useful for F7/tests).
    """
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(eas.get_all_level_actors())

    report = _scan(actors, skip_hidden)

    if widget is not None:
        _push_to_widget(widget, report, skip_hidden)
    else:
        _log_report(report, skip_hidden)

    return report


def _scan(actors: list, skip_hidden: bool) -> MeshStatsReport:
    total = len(actors)
    if total == 0:
        report = MeshStatsReport()
        report.scanned_at = datetime.now()
        return report

    with unreal.ScopedSlowTask(total, "Scanning level for mesh stats...") as task:
        task.make_dialog(True)

        def _should_cancel() -> bool:
            return bool(task.should_cancel())

        def _on_progress() -> None:
            task.enter_progress_frame(1)

        return collect_mesh_stats(
            actors=actors,
            should_cancel=_should_cancel,
            on_progress=_on_progress,
            skip_hidden=skip_hidden,
        )


# ─── Output Log fallback (menu-direct path) ─────────────────────────


def _log_report(report: MeshStatsReport, skip_hidden: bool) -> None:
    if report.cancelled:
        unreal.log_warning("[F2] ⚠ partial result (cancelled)")
    lines = [
        f"Static Mesh Actors:    {report.actor_count:,}",
        f"Total Triangles:       {report.total_triangles:,}",
        f"Total Vertices:        {report.total_vertices:,}",
        f"Material Sections:     {report.total_primitives:,}",
        f"Material Slots (sum):  {report.total_material_slots:,}",
        f"Unique Materials:      {report.unique_materials:,}",
        f"Unique Static Meshes:  {report.unique_static_meshes:,}",
        f"Nanite-Enabled Actors: {report.nanite_enabled_actors:,} / {report.actor_count:,}",
    ]
    if skip_hidden:
        lines.append(f"Hidden Skipped:        {report.skipped_hidden_count:,}")
    if report.scanned_at:
        lines.append(
            f"Scanned:               {report.scanned_at.strftime(_DATETIME_FMT)}"
        )
    for line in lines:
        unreal.log(f"[F2] {line}")


# ─── EUW push (widget path) ─────────────────────────────────────────


def _push_to_widget(widget, report: MeshStatsReport, skip_hidden: bool) -> None:
    """Set text on each ``lbl_*`` Text Block and toggle conditional ones.

    The EUW Blueprint must:
        - Expose every label as a Blueprint variable (Text Block with
          "Is Variable" checked) using the canonical names below.
        - Ship ``lbl_hidden_skipped`` and ``lbl_partial_badge`` as
          ``Collapsed`` by default — this function sets them Visible
          only when relevant.
    """
    _set_text(widget, "lbl_actor_count",
              f"Static Mesh Actors: {report.actor_count:,}")
    _set_text(widget, "lbl_triangles",
              f"Total Triangles: {report.total_triangles:,}")
    _set_text(widget, "lbl_vertices",
              f"Total Vertices: {report.total_vertices:,}")
    _set_text(widget, "lbl_primitives",
              f"Material Sections (Potential Draw Calls): {report.total_primitives:,}")
    _set_text(widget, "lbl_material_slots",
              f"Material Slots (total): {report.total_material_slots:,}")
    _set_text(widget, "lbl_unique_materials",
              f"Unique Materials: {report.unique_materials:,}")
    _set_text(widget, "lbl_unique_meshes",
              f"Unique Static Meshes: {report.unique_static_meshes:,}")
    _set_text(widget, "lbl_nanite",
              f"Nanite-Enabled Actors: {report.nanite_enabled_actors:,} / {report.actor_count:,}")

    scanned_text = (
        report.scanned_at.strftime(_DATETIME_FMT) if report.scanned_at else "-"
    )
    _set_text(widget, "lbl_scanned_at", f"Scanned: {scanned_text}")

    _set_text(widget, "lbl_hidden_skipped",
              f"Hidden Skipped: {report.skipped_hidden_count:,}")
    _set_visible(widget, "lbl_hidden_skipped", skip_hidden)

    _set_text(widget, "lbl_partial_badge", "⚠ 부분 결과 (취소됨)")
    _set_visible(widget, "lbl_partial_badge", report.cancelled)


# ─── F3: Instance detection runner ──────────────────────────────────


def run_detect_instances(
    threshold: int = 10,
    csv_out_path: Optional[str] = None,
) -> InstanceDetectionReport:
    """F3 entry point — detect ISM candidate groups and emit CSV + log.

    Progress is 2-phase:
        Phase A — "Gathering level actors..." (1 tick, cosmetic).
                  ``get_all_level_actors()`` is cached upstream of the
                  ScopedSlowTask so we know N before sizing the dialog;
                  this tick exists as a UX marker only.
        Phase B — "Detecting instance groups... (i/N)" (N ticks).

    Args:
        threshold: min group size to list as a candidate. Report always
            holds every group regardless; threshold only filters the
            ``candidate_groups`` property and therefore the CSV rows.
        csv_out_path: override destination. Default:
            ``{project_saved_dir}/CAD_Optimizer/instance_report_{ts}.csv``.

    Returns:
        InstanceDetectionReport — caller-usable directly (tests, F7).
    """
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Gather up front so ScopedSlowTask can be sized. The Phase A tick
    # below is a cosmetic acknowledgement of this already-done work.
    actors = list(eas.get_all_level_actors())
    n = len(actors)
    total_work = 1 + n

    was_cancelled = False
    progress_counter = 0

    with unreal.ScopedSlowTask(total_work, "F3: Instance Detection") as task:
        task.make_dialog(True)
        task.enter_progress_frame(1, "Gathering level actors...")

        def _should_cancel() -> bool:
            nonlocal was_cancelled
            if task.should_cancel():
                was_cancelled = True
                return True
            return False

        def _on_progress() -> None:
            nonlocal progress_counter
            progress_counter += 1
            task.enter_progress_frame(
                1,
                f"Detecting instance groups... ({progress_counter}/{n})",
            )

        report = detect_instance_groups(
            actors=actors,
            threshold=threshold,
            should_cancel=_should_cancel,
            on_progress=_on_progress,
        )

    csv_path = _write_instance_csv(report, csv_out_path)
    _log_instance_summary(report, was_cancelled, csv_path)
    return report


def _write_instance_csv(
    report: InstanceDetectionReport,
    csv_out_path: Optional[str],
) -> str:
    """Emit CSV with 3-line comment header + candidate rows. Returns path."""
    now = datetime.now()
    if csv_out_path is None:
        saved_dir = unreal.Paths.project_saved_dir()
        out_dir = os.path.join(saved_dir, "CAD_Optimizer")
        os.makedirs(out_dir, exist_ok=True)
        csv_out_path = os.path.join(
            out_dir, f"instance_report_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        )

    with open(csv_out_path, "w", newline="", encoding="utf-8-sig") as f:
        f.write("# GMTCK CAD Optimizer - F3 Instance Detection Report\n")
        f.write(f"# Generated: {now.strftime(_DATETIME_FMT)}\n")
        f.write(
            f"# Threshold: {report.threshold} | "
            f"Recommendation: ISM for Nanite-first rendering\n"
        )
        if report.material_slot_mismatch_count > 0:
            f.write(
                f"# Slot mismatches detected: "
                f"{report.material_slot_mismatch_count}\n"
            )
        writer = csv.writer(f)
        writer.writerow([
            "rank",
            "count",
            "mesh_path",
            "materials",
            "mobility",
            "estimated_drawcall_savings",
            "sample_actor_labels",
        ])
        for rank, g in enumerate(report.candidate_groups, start=1):
            writer.writerow([
                rank,
                g.count,
                g.key.mesh_path,
                ";".join(g.key.materials),
                g.key.mobility_name,
                (g.count - 1) * len(g.key.materials),
                ";".join(g.get_labels(limit=3)),
            ])

    return csv_out_path


def _log_instance_summary(
    report: InstanceDetectionReport,
    was_cancelled: bool,
    csv_path: str,
) -> None:
    prefix = "[CANCELED — partial results] " if was_cancelled else ""
    other = report.total_actors_scanned - report.static_mesh_actors
    lines = [
        f"{prefix}[CAD_Optimizer F3] Instance Detection Complete",
        f"  Scanned: {report.total_actors_scanned} actors "
        f"({report.static_mesh_actors} StaticMeshActor, {other} other)",
        f"  Skipped: {report.skipped_no_mesh} no-mesh, "
        f"{report.skipped_no_component} no-component, "
        f"{report.skipped_non_static} non-static",
    ]
    if report.material_slot_mismatch_count > 0:
        lines.append(
            f"  Slot mismatches: {report.material_slot_mismatch_count}"
        )
    lines.extend([
        f"  Groups: {len(report.groups)} unique "
        f"(threshold={report.threshold}, "
        f"{len(report.candidate_groups)} candidates)",
        f"  Est. drawcall reduction: "
        f"{report.estimated_drawcall_reduction} (추정치)",
    ])

    top = report.candidate_groups[:10]
    if top:
        lines.append("  Top 10 candidates:")
        for i, g in enumerate(top, start=1):
            lines.append(
                f"    #{i:<2} {g.count}x  {g.key.mesh_path} "
                f"[{g.key.mobility_name}]"
            )

    lines.append(f"  Full CSV: {csv_path}")

    for line in lines:
        unreal.log(line)


# ─── F4: Small part detection runner ────────────────────────────────


def run_detect_small_parts(
    threshold_cm: float = 1.0,
    csv_out_path: Optional[str] = None,
) -> SmallPartDetectionReport:
    """F4 entry point — measure bbox diagonals, emit CSV + log summary.

    Single entry point. Preset menu items and EUW Custom button all call
    this with ``threshold_cm`` set explicitly — no wrapper functions.

    Progress is 2-phase, mirroring F3:
        Phase A — "Gathering level actors..." (1 tick, cosmetic).
        Phase B — "Measuring bboxes... (i/N)" (N ticks).

    Args:
        threshold_cm: bbox diagonal cut-off. Stored on the report; the
            ``small_parts`` filter uses it. Re-thresholding is free via
            ``report.simulate_thresholds`` — the simulation table in the
            log already shows it.
        csv_out_path: override destination. Default:
            ``{project_saved_dir}/CAD_Optimizer/small_part_report_{ts}.csv``.

    Returns:
        SmallPartDetectionReport — caller-usable directly (tests, F7).
    """
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(eas.get_all_level_actors())
    n = len(actors)
    total_work = 1 + n

    was_cancelled = False
    progress_counter = 0

    with unreal.ScopedSlowTask(total_work, "F4: Small Part Detection") as task:
        task.make_dialog(True)
        task.enter_progress_frame(1, "Gathering level actors...")

        def _should_cancel() -> bool:
            nonlocal was_cancelled
            if task.should_cancel():
                was_cancelled = True
                return True
            return False

        def _on_progress() -> None:
            nonlocal progress_counter
            progress_counter += 1
            task.enter_progress_frame(
                1,
                f"Measuring bboxes... ({progress_counter}/{n})",
            )

        report = detect_small_parts(
            actors=actors,
            threshold_cm=threshold_cm,
            should_cancel=_should_cancel,
            on_progress=_on_progress,
        )

    # F5: classify each measurement's parent_part_label.
    # Parallel list — same length & order as report.measurements.
    categories = classify_measurements(report.measurements)

    csv_path = _write_small_parts_csv(report, categories, csv_out_path)
    _log_small_parts_summary(report, categories, was_cancelled, csv_path)
    return report


def _preset_name_for(threshold_cm: float) -> Optional[str]:
    """Reverse-lookup ``PRESETS`` for the [Preset: X] tag in logs/CSV."""
    for name, value in PRESETS.items():
        if math.isclose(threshold_cm, value, abs_tol=1e-6):
            return name
    return None


def _write_small_parts_csv(
    report: SmallPartDetectionReport,
    categories: List[str],
    csv_out_path: Optional[str],
) -> str:
    """Emit CSV with comment header + raw measurement rows + nx_category.

    ``categories`` is a parallel list to ``report.measurements`` (same
    length, same order). Caller is responsible for that invariant —
    F5 ``classify_measurements`` produces it.

    Returned path is absolute and forward-slash normalized for Output
    Log readability; the actual file write goes to the same location
    Windows would resolve either way.
    """
    now = datetime.now()
    if csv_out_path is None:
        saved_dir = unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_saved_dir()
        )
        out_dir = os.path.join(saved_dir, "CAD_Optimizer")
        os.makedirs(out_dir, exist_ok=True)
        csv_out_path = os.path.join(
            out_dir, f"small_part_report_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        )

    preset_name = _preset_name_for(report.threshold_cm)
    preset_line = f"# Preset (if matched): {preset_name}\n" if preset_name else "# Preset (if matched): -\n"

    with open(csv_out_path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(f"# Generated: {now.strftime(_DATETIME_FMT)}\n")
        f.write(
            f"# Threshold (small if diagonal < this): "
            f"{report.threshold_cm:.2f} cm\n"
        )
        f.write(preset_line)
        f.write(
            "# Note: bbox is world-space (scale-applied). UE unit = cm.\n"
        )
        f.write(
            "# Datasmith hierarchy: parent_part_label = real part name "
            "(leaf actor_label is usually \"Geometry*\").\n"
        )
        f.write(
            "# parent_chain_path uses noise-filtered attach chain. "
            "is_multi_leaf flags parts split across N leaves.\n"
        )
        f.write(
            "# nx_category: NX naming classification (V2 patterns from "
            "docs/concepts/nx_naming_patterns.md).\n"
        )
        f.write(
            "# material_count: smc.get_num_materials() returns. "
            "override_status: no_slot|slot_empty|has_override (3-value enum, "
            "see docs/concepts/material_analysis_c1yc_2_mcm.md Section 8).\n"
        )
        writer = csv.writer(f)
        writer.writerow([
            "rank",
            "actor_label",
            "parent_part_label",     # 사용자 가독성 핵심
            "nx_category",           # F5 — 박제: docs/concepts/nx_naming_patterns.md
            "folder_path",
            "mesh_path",
            "bbox_x_cm",
            "bbox_y_cm",
            "bbox_z_cm",
            "bbox_diagonal_cm",
            "bbox_max_edge_cm",
            "bbox_volume_cm3",
            "mobility",
            "is_small",
            "parent_leaf_count",
            "is_multi_leaf",
            "material_count",        # F6 — 박제: docs/concepts/material_analysis_c1yc_2_mcm.md
            "override_status",       # F6
            "material_path_top1",    # F6
            "parent_chain_path",     # longest column → 마지막
        ])
        for rank, (m, cat) in enumerate(
            zip(report.measurements, categories), start=1
        ):
            writer.writerow([
                rank,
                m.get_label(),
                m.parent_part_label,
                cat,
                m.folder_path,
                m.mesh_path,
                f"{m.bbox_x_cm:.3f}",
                f"{m.bbox_y_cm:.3f}",
                f"{m.bbox_z_cm:.3f}",
                f"{m.bbox_diagonal_cm:.3f}",
                f"{m.bbox_max_edge_cm:.3f}",
                f"{m.bbox_volume_cm3:.3f}",
                m.mobility_name,
                report.is_small(m),
                m.parent_leaf_count,
                m.is_multi_leaf,
                m.material_count,
                m.override_status,
                m.material_path_top1,
                m.parent_chain_path,
            ])

    return csv_out_path.replace("\\", "/")


def _format_simulation_table(
    simulation: Iterable[Tuple[float, int]],
    current_threshold_cm: float,
) -> List[str]:
    """Build ASCII table for the multi-threshold simulation block.

    The 'current' row's right border is replaced with a `←current` marker
    so the active threshold pops out visually.
    """
    rows: List[str] = []
    rows.append("    +------------+--------------+")
    rows.append("    |  Threshold | Small parts  |")
    rows.append("    +------------+--------------+")
    for t, count in simulation:
        is_current = math.isclose(t, current_threshold_cm, abs_tol=1e-6)
        threshold_cell = f"{t:>5.1f} cm"
        count_cell = f"{count:>10}"
        row = f"    |  {threshold_cell}  | {count_cell}   |"
        if is_current:
            # Drop the trailing border to anchor the marker
            row = row.rstrip(" |") + "  ←current"
        rows.append(row)
    rows.append("    +------------+--------------+")
    return rows


_DISJOINT_WARNING = (
    "  ⚠ Note: F4 measures whole-actor bbox. Meshes containing disjoint "
    "geometry\n"
    "    (e.g. left+right symmetric parts merged) report large bbox and "
    "may not\n"
    "    appear in 'Small parts'. Phase 2 will handle disjoint splitting."
)


def _format_parent_for_log(m, max_label_len: int = 50) -> str:
    """Format the parent identification segment of a smallest-10 row.

    Returns either:
        ``parent: <truncated_label>``           — when parent_part_label set
        ``parent: <root>  actor: <leaf_label>`` — when no attach parent
    """
    if m.parent_part_label:
        label = m.parent_part_label
        if len(label) > max_label_len:
            label = label[: max_label_len - 3] + "..."
        return f"parent: {label}"
    return f"parent: <root>  actor: {m.get_label()}"


def _format_category_block(
    counts: "OrderedDict[str, int]",
    total: int,
) -> List[str]:
    """8 categories + UNCATEGORIZED, fixed-width columns. Uses
    NX_CATEGORY_ORDER so category rows stay in canonical order even
    if some categories have count 0.
    """
    lines = [
        f"  NX category distribution ({total:,} measured):",
    ]
    for cat in NX_CATEGORY_ORDER:
        cnt = counts[cat]
        pct = (cnt / total * 100.0) if total else 0.0
        lines.append(
            f"    {cat:<14s} : {cnt:>6,} ({pct:>4.1f}%)"
        )
    lines.append(
        "  See docs/concepts/nx_naming_patterns.md for derivation."
    )
    return lines


def _log_small_parts_summary(
    report: SmallPartDetectionReport,
    categories: List[str],
    was_cancelled: bool,
    csv_path: str,
) -> None:
    prefix = "[CANCELED — partial results] " if was_cancelled else ""

    other = report.total_actors_scanned - report.static_mesh_actors
    measured = len(report.measurements)
    small_count = len(report.small_parts)
    pct = (small_count / measured * 100.0) if measured else 0.0
    preset_name = _preset_name_for(report.threshold_cm)
    preset_str = f" [Preset: {preset_name}]" if preset_name else ""

    lines = [
        f"{prefix}[CAD_Optimizer F4] Small Part Detection Complete",
        f"  Scanned: {report.total_actors_scanned} actors "
        f"({report.static_mesh_actors} StaticMeshActor, {other} other)",
        f"  Skipped: {report.skipped_no_root} no-root, "
        f"{report.skipped_no_mesh} no-mesh, "
        f"{report.skipped_zero_bbox} zero-bbox",
        f"  Root-level (no attach parent, measured): "
        f"{report.skipped_no_attach_parent}",
        f"  Measured: {measured} actors",
        f"  Threshold: {report.threshold_cm:.2f} cm (diagonal){preset_str}",
        f"  Small parts: {small_count} / {measured} ({pct:.1f}%)",
    ]

    percentiles = report.diagonal_percentiles
    if percentiles:
        lines.append(
            f"  Diagonal distribution: "
            f"P10={percentiles['p10']:.1f}cm, "
            f"P50={percentiles['p50']:.1f}cm, "
            f"P90={percentiles['p90']:.1f}cm"
        )
    else:
        lines.append("  Diagonal distribution: (no measurements)")

    lines.append("")
    lines.append(
        "  Multi-threshold simulation (free re-threshold from same "
        "measurement):"
    )
    simulation = report.simulate_thresholds(SIMULATION_THRESHOLDS_CM)
    lines.extend(_format_simulation_table(simulation, report.threshold_cm))

    lines.append("")
    lines.append("  Smallest 10 (by diagonal):")
    smallest = report.measurements[:10]
    if smallest:
        for i, m in enumerate(smallest, start=1):
            multi_tag = (
                f"  multi={m.parent_leaf_count}" if m.is_multi_leaf else ""
            )
            lines.append(
                f"    #{i:<2} {m.bbox_diagonal_cm:>6.2f}cm  "
                f"{_format_parent_for_log(m):<55s}  "
                f"[{m.mobility_name}]{multi_tag}"
            )
    else:
        lines.append("    (no measurements)")

    # F5: NX category distribution
    lines.append("")
    counts = category_counts(categories)
    lines.extend(_format_category_block(counts, len(report.measurements)))

    # F6: Material override status anchor
    lines.append("")
    lines.extend(_format_override_status_block(report.measurements))

    lines.append("")
    lines.append(_DISJOINT_WARNING)
    lines.append("")
    lines.append("  💡 다른 threshold로 다시 돌리기:")
    lines.append("     run_detect_small_parts(threshold_cm=2.0)")
    lines.append("     또는 EUW에서 Custom 입력 후 Run")
    lines.append(f"  Full CSV: {csv_path}")

    for line in lines:
        unreal.log(line)


# ─── F6: Material override status (F4 log anchor) + inventory runner ──


def _format_override_status_block(measurements) -> List[str]:
    """Material override status — 3-value enum (실차 검증 기반).

    박제 (docs/concepts/material_analysis_c1yc_2_mcm.md Section 8):
        - NO_SLOT: smc has no slots
        - SLOT_EMPTY: slot exists but asset None → mesh default fallback
        - HAS_OVERRIDE: slot + asset both present
    SLOT_EMPTY 비율은 Datasmith CAD에서 흔한 정상 fallback 상태이므로
    경고 X. anchor 텍스트로 박제 reference 노출.
    """
    no_slot = sum(1 for m in measurements if m.override_status == NO_SLOT)
    slot_empty = sum(1 for m in measurements if m.override_status == SLOT_EMPTY)
    has_override = sum(1 for m in measurements if m.override_status == HAS_OVERRIDE)
    total = len(measurements) or 1  # division-by-zero 가드
    return [
        "  Material override status:",
        f"    no_slot     : {no_slot:>6,} ({no_slot / total * 100.0:>4.1f}%) "
        f"← no material slot",
        f"    slot_empty  : {slot_empty:>6,} ({slot_empty / total * 100.0:>4.1f}%) "
        f"← slot exists, asset None → mesh default fallback (typical for Datasmith CAD)",
        f"    has_override: {has_override:>6,} ({has_override / total * 100.0:>4.1f}%) "
        f"← slot + asset present",
        "  See docs/concepts/material_analysis_c1yc_2_mcm.md for details.",
    ]


def run_material_inventory(
    csv_out_path: Optional[str] = None,
) -> None:
    """F6 entry point — full material asset inventory.

    Walks all StaticMeshActors, builds per-material usage counts,
    writes inventory CSV + Output Log summary.
    """
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(eas.get_all_level_actors())
    if not actors:
        unreal.log_warning("[CAD_Optimizer F6] Empty level — nothing to inventory.")
        return

    cancelled = [False]

    with unreal.ScopedSlowTask(len(actors), "F6: Building material inventory...") as task:
        task.make_dialog(True)

        def _should_cancel() -> bool:
            if task.should_cancel():
                cancelled[0] = True
                return True
            return False

        def _on_progress() -> None:
            task.enter_progress_frame(1)

        report = build_inventory(
            actors,
            should_cancel=_should_cancel,
            on_progress=_on_progress,
        )

    csv_path = _write_inventory_csv(report, csv_out_path)
    _log_inventory_summary(report, cancelled[0], csv_path)


def _write_inventory_csv(
    report: MaterialInventoryReport,
    csv_out_path: Optional[str],
) -> str:
    """Write material asset inventory CSV — one row per unique material."""
    now = datetime.now()
    if csv_out_path is None:
        saved_dir = unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_saved_dir()
        )
        out_dir = os.path.join(saved_dir, "CAD_Optimizer")
        os.makedirs(out_dir, exist_ok=True)
        csv_out_path = os.path.join(
            out_dir, f"material_inventory_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        )

    with open(csv_out_path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(f"# Generated: {now.strftime(_DATETIME_FMT)}\n")
        f.write(f"# Level actors scanned: {report.total_actors_scanned}\n")
        f.write(f"# StaticMeshActor count: {report.sma_count}\n")
        f.write(f"# Total unique materials: {report.total_unique_materials}\n")
        f.write("# usage_via_override = counted from smc.get_material(i) (HAS_OVERRIDE actors)\n")
        f.write(
            "# usage_via_default = counted when actor SLOT_EMPTY/NO_SLOT "
            "(mesh default fallback)\n"
        )
        f.write(
            "# override_status (3-value enum): no_slot|slot_empty|has_override. "
            "See docs/concepts/material_analysis_c1yc_2_mcm.md Section 8.\n"
        )

        writer = csv.writer(f)
        writer.writerow([
            "rank",
            "material_path",
            "usage_via_override",
            "usage_via_default",
            "total_usage",
            "category",
            "is_instance",
            "is_base",
        ])
        for rank, a in enumerate(report.assets, start=1):
            writer.writerow([
                rank,
                a.material_path,
                a.usage_via_override,
                a.usage_via_default,
                a.total_usage,
                a.category,
                a.is_instance,
                a.is_base,
            ])

    return csv_out_path.replace("\\", "/")


def _log_inventory_summary(
    report: MaterialInventoryReport,
    was_cancelled: bool,
    csv_path: str,
) -> None:
    prefix = "[CANCELED — partial results] " if was_cancelled else ""
    other = report.total_actors_scanned - report.sma_count
    sma_safe = report.sma_count if report.sma_count else 1
    no_slot_pct = report.no_slot_count / sma_safe * 100.0
    slot_empty_pct = report.slot_empty_count / sma_safe * 100.0
    has_pct = report.has_override_count / sma_safe * 100.0

    lines = [
        f"{prefix}[CAD_Optimizer F6] Material Inventory Complete",
        f"  Scanned: {report.total_actors_scanned:,} actors "
        f"({report.sma_count:,} StaticMeshActor, {other:,} other)",
        f"  Skipped: {report.skipped_no_smc} no-smc, "
        f"{report.skipped_no_sm} no-mesh",
        f"  Override status: "
        f"{report.no_slot_count:,} no_slot ({no_slot_pct:.1f}%), "
        f"{report.slot_empty_count:,} slot_empty ({slot_empty_pct:.1f}%), "
        f"{report.has_override_count:,} has_override ({has_pct:.1f}%)",
        f"  Total unique materials: {report.total_unique_materials}",
        "",
    ]

    # Top 10 materials
    lines.append("  Top 10 materials by total_usage:")
    top = report.assets[:10]
    if top:
        for rank, a in enumerate(top, start=1):
            instance_tag = "MI" if a.is_instance else "M " if a.is_base else "??"
            lines.append(
                f"    #{rank:<2}  {a.total_usage:>6,} uses  "
                f"[{a.category:<10}] [{instance_tag}]  {a.material_path}"
            )
    else:
        lines.append("    (no materials found)")

    lines.append("")

    # Category distribution
    counts = material_category_counts(report.assets)
    total_assets = report.total_unique_materials if report.total_unique_materials else 1
    lines.append("  Material category distribution (unique assets):")
    for cat in MATERIAL_CATEGORY_ORDER:
        cnt = counts[cat]
        pct = (cnt / total_assets * 100.0) if report.total_unique_materials else 0.0
        lines.append(f"    {cat:<10} : {cnt:>4,} ({pct:>4.1f}%)")
    lines.append("  See docs/concepts/material_analysis_c1yc_2_mcm.md for analysis.")
    lines.append("")
    lines.append(f"  Full CSV: {csv_path}")

    for line in lines:
        unreal.log(line)


# ─── F7: Integrated Report ──────────────────────────────────────────


def _latest_csv(out_dir: str, prefix: str) -> str:
    """가장 최근 timestamp의 CSV 경로 반환. 없으면 빈 문자열.

    Filename pattern: ``<prefix><YYYYMMDD_HHMMSS>.csv``. lexicographic
    sort = chronological (timestamp 형식이 zero-padded).
    """
    if not os.path.isdir(out_dir):
        return ""
    candidates = sorted(
        f for f in os.listdir(out_dir)
        if f.startswith(prefix) and f.endswith(".csv")
    )
    if not candidates:
        return ""
    return os.path.join(out_dir, candidates[-1]).replace("\\", "/")


def _get_current_level_name() -> str:
    """현재 에디터의 level 이름. 실패 시 빈 문자열 (정상 경로 — F7 markdown은
    그냥 미기록으로 표시). UnrealEditorSubsystem은 5.2+에서 표준."""
    try:
        ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = ues.get_editor_world() if ues else None
        if world:
            return world.get_name()
    except Exception:
        pass
    return ""


def _infer_vehicle_code(level_name: str) -> str:
    """레벨명에서 차량 코드 추출. ``L_<code>`` prefix 제거."""
    if level_name.startswith("L_"):
        return level_name[2:]
    return level_name


def run_integrated_report() -> None:
    """F7 entry point — orchestrate F2/F3/F4/F6 + build markdown report.

    한 클릭으로 전체 측정 + 통합 박제. 각 F-task는 자체 CSV/Output Log
    부수 효과 발생 (F3 instance_report / F4 small_part_report /
    F6 material_inventory). F7은 그 결과들을 집계해 단일 markdown
    (primary 산출물) 생성.

    페이즈:
        1. F2 Mesh Stats (in-memory)
        2. F3 Instance Detection (CSV side-effect)
        3. F4 Small Part Detection (CSV side-effect, F5 nx_category +
           F6 material 컬럼 포함)
        4. F6 Material Inventory (CSV side-effect, asset-level)
        5. Locate latest supporting CSVs + build markdown + write to disk
    """
    unreal.log("=" * 60)
    unreal.log("[CAD_Optimizer F7] Starting integrated measurement pipeline...")
    unreal.log("=" * 60)

    # Phase 1-4: 각 F-task 실행. 각각 자체 ScopedSlowTask + Output Log 발생.
    # F4 threshold = Tiny (0.5 cm) — F4/F5 박제 baseline과 일치
    # (docs/measurements/f4_c1yc_2_mcm.md, f5_nx_distribution_c1yc_2_mcm.md
    # 둘 다 Tiny 기준). 차량 간 비교의 baseline 일관성 확보.
    f2_report = run_scan_level(widget=None, skip_hidden=False)
    f3_report = run_detect_instances()
    f4_report = run_detect_small_parts(threshold_cm=PRESETS["Tiny"])
    run_material_inventory()

    # Phase 5: 산출물 경로 수집 + markdown 생성.
    saved_dir = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_saved_dir()
    )
    out_dir = os.path.join(saved_dir, "CAD_Optimizer")

    f3_csv = _latest_csv(out_dir, "instance_report_")
    f4_csv = _latest_csv(out_dir, "small_part_report_")
    f6_csv = _latest_csv(out_dir, "material_inventory_")

    level_name = _get_current_level_name()
    vehicle_code = _infer_vehicle_code(level_name) if level_name else ""

    vm = VehicleMeta(
        vehicle_code=vehicle_code,
        level_name=level_name,
        plugin_commit="(see git log)",
        measured_at=datetime.now(),
        threshold_cm=f4_report.threshold_cm,
    )

    md = build_report(
        f2_stats=f2_report,
        f3_stats=f3_report,
        f4_report=f4_report,
        vehicle_meta=vm,
        f4_csv_path=f4_csv,
        f6_inventory_csv_path=f6_csv,
        f3_csv_path=f3_csv,
    )

    md_filename = f"integrated_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    md_path = os.path.join(out_dir, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    md_path_norm = md_path.replace("\\", "/")

    # Output Log A' pattern — Primary / Supporting 명시.
    unreal.log("=" * 60)
    unreal.log("[CAD_Optimizer F7] Integrated report generated.")
    unreal.log(f"  Primary:    {md_path_norm}")
    unreal.log(f"  Supporting: {f4_csv}")
    unreal.log(f"              {f6_csv}")
    unreal.log(f"              {f3_csv}")
    unreal.log("=" * 60)


# ─── F8: Metadata Tagging ───────────────────────────────────────────


def _make_f8_csv_path() -> str:
    """F8 CSV 경로 생성. F4/F6 inventory CSV와 같은 디렉터리.

    Note:
        F4 / F6 / F7 path helpers는 각자 inline 구현됨 (Saved/CAD_Optimizer/
        + prefix + timestamp). 본 helper도 동일 패턴 — Phase 1 cleanup 시
        path helper 통합 검토 가능 (현재는 scope creep 회피).
    """
    saved_dir = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_saved_dir()
    )
    out_dir = os.path.join(saved_dir, "CAD_Optimizer")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(out_dir, f"f8_metadata_{ts}.csv")


def _print_f8_output_log(result: TagApplicationResult) -> None:
    """F8 결과 Output Log 박제. Tagged vs Implicit Keep 시각적 분리."""
    unreal.log("=" * 60)
    unreal.log("[CAD_Optimizer F8] Metadata Tagging Complete")
    unreal.log("=" * 60)
    unreal.log(f"Total measurements: {result.total_actors:,}")
    unreal.log("")
    unreal.log(f"Tagged (actor.tags applied): {result.tagged:,}")
    for tier in TIER_ORDER:
        if tier == TIER_KEEP:
            continue  # Keep은 implicit, 아래 분리 출력
        count = result.tier_counts.get(tier, 0)
        unreal.log(f"  {tier:<25s}: {count:>6,}")
    unreal.log("")
    unreal.log(
        f"Implicit Keep (CSV only, no actor.tags): {result.implicit_keep:,}"
    )
    if result.not_found_in_level > 0:
        unreal.log_warning(
            f"Not found in level (stale actor refs): "
            f"{result.not_found_in_level:,}"
        )
    unreal.log("")
    unreal.log(f"CSV: {result.csv_path}")
    unreal.log_warning(
        "⚠ Level dirty — File → Save All to persist tags"
    )
    unreal.log("=" * 60)


def run_apply_metadata_tags() -> None:
    """F8 entry point — F4 fresh re-run + 4-tier metadata tag 부여.

    Tier 결정 입력: bbox_diagonal (F4) + nx_category (F5) + override_status (F6).
    Tag prefix: ``CADOpt_F8_``. Idempotent — 기존 ``CADOpt_F8_*`` tag 제거 후
    새로 부여. 비-F8 tag 보존.

    Implicit Keep: ``not is_small`` actor는 tag 부여 X (outliner 노이즈 회피).
    단 CSV에는 모든 actor 박제 (실제 적용 상태 = CSV가 truth).

    Visibility culling은 Phase 3 scope. 본 함수는 metadata 준비만.
    """
    unreal.log("=" * 60)
    unreal.log("[CAD_Optimizer F8] Starting metadata tagging pipeline...")
    unreal.log("=" * 60)

    # F4 fresh run — F5 nx_category + F6 override_status도 measurement 안에
    # baked-in. SmallPartMeasurement.actor 직접 사용 (같은 세션이라 ref 유효).
    f4_report = run_detect_small_parts(threshold_cm=PRESETS["Tiny"])
    total = len(f4_report.measurements)

    csv_path = _make_f8_csv_path()

    with unreal.ScopedSlowTask(total, "F8 Metadata Tagging...") as slow_task:
        slow_task.make_dialog(True)

        def _progress_adapter(current: int, total_: int, msg: str) -> bool:
            """metadata_tagger callback adapter.
            False 반환 시 metadata_tagger가 mid-stream 중단 (idempotent라 안전).
            """
            slow_task.enter_progress_frame(1, msg)
            return not bool(slow_task.should_cancel())

        result = apply_tags_to_level(
            f4_report,
            threshold_cm=PRESETS["Tiny"],
            csv_out_path=csv_path,
            progress_callback=_progress_adapter,
            plugin_commit="(see git log)",
        )

    _print_f8_output_log(result)


# ─── Widget helper plumbing (shared by F2) ──────────────────────────


def _resolve_label(widget, name: str):
    """Blueprint-exposed var first, fall back to ``get_widget_from_name``."""
    label = getattr(widget, name, None)
    if label is not None:
        return label
    try:
        return widget.get_widget_from_name(name)
    except Exception:
        return None


def _set_text(widget, name: str, text: str) -> None:
    label = _resolve_label(widget, name)
    if label is None:
        unreal.log_warning(f"[F2] label '{name}' not found on widget")
        return
    try:
        label.set_text(text)
    except Exception as exc:
        unreal.log_warning(f"[F2] failed to set text on '{name}': {exc}")


def _set_visible(widget, name: str, visible: bool) -> None:
    label = _resolve_label(widget, name)
    if label is None:
        return
    try:
        label.set_visibility(
            unreal.SlateVisibility.VISIBLE
            if visible
            else unreal.SlateVisibility.COLLAPSED
        )
    except Exception as exc:
        unreal.log_warning(f"[F2] failed to set visibility on '{name}': {exc}")
