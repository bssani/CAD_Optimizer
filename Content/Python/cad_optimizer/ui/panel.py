"""F2 runner + EUW glue.

``run_scan_level`` is the single entry point:
    - Called from the "Scan Level" button inside EUW → pushes stats
      into the widget's ``lbl_*`` Text Blocks.
    - Called from the Tools > Scan Level menu item → ``widget=None``
      and results are dumped to the Output Log.

Progress + cancel come from ``unreal.ScopedSlowTask`` directly, not
``SlowIter``, because ``stats.collect_mesh_stats`` is callback-driven
and must stay ignorant of SlowIter. Same underlying freeze-prevention
mechanism; F0 pattern preserved.
"""
from datetime import datetime
from typing import Optional

import unreal

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
