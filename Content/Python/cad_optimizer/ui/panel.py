"""F2 + F3 runners + EUW glue.

F2 — ``run_scan_level`` (mesh stats diagnostic):
    - EUW button → pushes stats into the widget's ``lbl_*`` Text Blocks.
    - Tools > Scan Level → ``widget=None``, Output Log dump.

F3 — ``run_detect_instances`` (ISM candidate detection):
    - Tools > Detect Instances or EUW button → writes CSV report to
      ``{project_saved_dir}/CAD_Optimizer/instance_report_{ts}.csv``
      and logs a top-10 summary to Output Log.
    - Detection-only. Level/actors are never mutated.

Progress + cancel come from ``unreal.ScopedSlowTask`` directly, not
``SlowIter``, because the core modules (``stats``, ``instance_detector``)
are callback-driven and must stay ignorant of SlowIter. Same underlying
freeze-prevention mechanism; F0 pattern preserved.

EUW Blueprint guide for the F3 entry (Philip sets this up in-editor):

    Section: "F3 Instance Detection"
      - SpinBox (int) : Threshold, default=10, min=2, max=1000
                        (variable name: ``sb_f3_threshold``)
      - Button         : "Run Detection"
          OnClicked:
            sb_f3_threshold.Value → Format Text:
              "cad_optimizer.ui.panel.run_detect_instances(threshold={0})"
            → Execute Python Command
    Reuses the Format Text pattern established in F2 (week02.md §3).
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Optional

import unreal

from cad_optimizer.instance_detector import (
    InstanceDetectionReport,
    detect_instance_groups,
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
        f"  Groups: {len(report.groups)} unique "
        f"(threshold={report.threshold}, "
        f"{len(report.candidate_groups)} candidates)",
        f"  Est. drawcall reduction: "
        f"{report.estimated_drawcall_reduction} (추정치)",
    ]

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
