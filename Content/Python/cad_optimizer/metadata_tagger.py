"""Metadata Tagger — F8.

Phase 3 visibility culling 대비 actor에 4-tier metadata tag 부여.
Phase 1 = tag 부여 + CSV 박제만. 실제 cull/LOD 적용은 Phase 3.

Tier 결정 입력:
- bbox_diagonal_cm (F4)
- nx_category (F5, parallel list — SmallPartMeasurement field 아님)
- override_status (F6, "no_slot" / "slot_empty" / "has_override")

Tier 규칙 (실차 검증 박제 docs/measurements/integrated_report_c1yc_2_mcm.md § 8/12):

    if bbox_diagonal_cm >= threshold_cm (default 0.5 cm):
        → CADOpt_F8_Keep            (tag 부재로 implicit, outliner 노이즈 회피)
    elif override_status == "slot_empty":
        if nx_category in {LATCH, BRACKET}: CADOpt_F8_Cull_High
        else:                                CADOpt_F8_Cull_Mid
    else:  # has_override or no_slot
        → CADOpt_F8_Review

설계 원칙:
- ``compute_tier`` = 순수 함수. ``unreal`` 의존 0 → 단위 테스트 가능 (F-pattern).
- ``apply_tags_to_level`` = actor mutation. ``unreal`` 의존 (별도 함수).
- Tag prefix ``CADOpt_F8_`` — outliner 검색 친화적, idempotent 재실행 시
  기존 F8 tag만 제거 후 새로 부여 (비-F8 tag 보존).
- Implicit Keep: not small actor는 tag 부재 = Keep. outliner 깔끔.
  단 CSV 박제는 모든 actor 행 기록 (완전성).

박제 reference:
- ``docs/measurements/integrated_report_c1yc_2_mcm.md`` §8/§12 — tier schema 근거
- ``docs/concepts/material_analysis_c1yc_2_mcm.md`` §8 — override_status enum
- ``docs/concepts/nx_naming_patterns.md`` — nx_category V2 regex
"""
from __future__ import annotations

import csv as csv_mod
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from cad_optimizer.small_part_detector import SmallPartDetectionReport


# Tag prefix + 4 tier names (idempotent prefix filter용).
TAG_PREFIX = "CADOpt_F8_"

TIER_CULL_HIGH = "CADOpt_F8_Cull_High"   # small AND slot_empty AND nx in [LATCH, BRACKET]
TIER_CULL_MID = "CADOpt_F8_Cull_Mid"     # small AND slot_empty (그 외 카테고리)
TIER_REVIEW = "CADOpt_F8_Review"          # small AND (has_override OR no_slot)
TIER_KEEP = "CADOpt_F8_Keep"              # not small (tag 부재로 implicit, CSV에만 기록)

# 4 tier canonical order — Output Log / CSV 안정성.
TIER_ORDER: List[str] = [
    TIER_CULL_HIGH,
    TIER_CULL_MID,
    TIER_REVIEW,
    TIER_KEEP,
]

# "Slot_empty 시 Cull_High 처리" 카테고리. § 8 cross-tab에서 small+slot_empty
# 의존도 최고인 LATCH(93.6%) + BRACKET(74.3% 그러나 small 0개) 묶음. BRACKET은
# small이 거의 없어 사실상 LATCH만 적용되지만 spec 일관성 위해 포함.
HIGH_TIER_NX_CATEGORIES = frozenset({"LATCH", "BRACKET"})


@dataclass
class TagApplicationResult:
    """F8 적용 결과 — Output Log + CSV 박제 입력."""

    total_actors: int                       # F4 measurements 길이
    tagged: int                             # is_small True (actor.tags 변경됨)
    implicit_keep: int                      # is_small False (tag 부재 = Keep)
    tier_counts: Dict[str, int] = field(default_factory=dict)  # 4 tier별 카운트
    not_found_in_level: int = 0             # F4 measurement.actor invalid (드물 케이스)
    csv_path: str = ""


# ─── Pure tier dispatch (unreal 의존 0) ─────────────────────────────


def compute_tier(
    bbox_diagonal_cm: float,
    nx_category: str,
    override_status: str,
    threshold_cm: float = 0.5,
) -> str:
    """4-tier dispatch. 박제 § 12 schema 그대로.

    Args:
        bbox_diagonal_cm: F4 measurement field.
        nx_category: F5 classification (e.g. "LATCH", "WIRING", "UNCATEGORIZED").
        override_status: F6 3-value enum ("no_slot" / "slot_empty" / "has_override").
        threshold_cm: small/not-small 경계. 기본 Tiny preset (0.5 cm).

    Returns:
        Tier 이름 문자열 (4개 중 하나).
    """
    is_small = bbox_diagonal_cm < threshold_cm
    if not is_small:
        return TIER_KEEP

    if override_status == "slot_empty":
        if nx_category in HIGH_TIER_NX_CATEGORIES:
            return TIER_CULL_HIGH
        return TIER_CULL_MID

    # has_override OR no_slot — 작지만 명시 binding 또는 slot 자체 없음
    return TIER_REVIEW


def compute_tiers_for_report(
    report: "SmallPartDetectionReport",
    threshold_cm: float = 0.5,
) -> List[str]:
    """Report 전체 measurements에 ``compute_tier`` 적용.

    classify_measurements를 1회 호출하여 nx_category list 생성 후 zip.
    반환은 parallel list (report.measurements와 같은 길이/순서).
    """
    from cad_optimizer.nx_naming import classify_measurements

    categories = classify_measurements(report.measurements)
    return [
        compute_tier(
            m.bbox_diagonal_cm,
            cat,
            m.override_status,
            threshold_cm,
        )
        for m, cat in zip(report.measurements, categories)
    ]


def count_tiers(tiers: List[str]) -> "Counter[str]":
    """4 tier 별 카운트 (TIER_ORDER 보존, 카운트 0 카테고리도 포함)."""
    raw = Counter(tiers)
    return Counter({t: raw.get(t, 0) for t in TIER_ORDER})


# ─── Level mutation (unreal 의존, Step 3 구현 예정) ─────────────────


# ─── Actor-side helpers (duck-typed, ``unreal`` 의존 0) ─────────────


def _actor_is_usable(actor) -> bool:
    """Actor 참조가 살아있는지 defensive 체크. F4 측정 후 사용자가 actor를
    삭제했거나 level reload된 경우 False.

    ``is_valid()`` 메서드는 UE Python wrapper의 표준 (UObject 기반). 없으면
    truthy check만 fallback.
    """
    if actor is None:
        return False
    if hasattr(actor, "is_valid"):
        try:
            return bool(actor.is_valid())
        except Exception:
            return False
    return True


def _safe_path(actor) -> str:
    try:
        return actor.get_path_name()
    except Exception:
        return ""


def _safe_label(actor) -> str:
    try:
        return actor.get_actor_label()
    except Exception:
        return ""


# ─── Public mutation API ────────────────────────────────────────────


def apply_tags_to_level(
    report: "SmallPartDetectionReport",
    threshold_cm: float = 0.5,
    csv_out_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], bool]] = None,
    plugin_commit: str = "",
) -> TagApplicationResult:
    """Level의 actor에 tier tag 부여 + CSV 박제. Idempotent.

    Args:
        report: F4 in-memory ``SmallPartDetectionReport``. ``measurements``
            의 ``actor`` field를 직접 참조 (lookup 불필요).
        threshold_cm: tier 결정 small 경계 (default Tiny 0.5 cm).
        csv_out_path: 박제 CSV 경로. None이면 CSV write 생략 (caller가 path
            구성하지 않은 경우).
        progress_callback: ``(current_index, total, msg) -> bool``. False
            반환 시 즉시 중단 (현재까지 변경 + CSV 박제 유지). Idempotent라
            mid-stream 중단 안전.
        plugin_commit: CSV 헤더에 박제할 git commit hash (caller 제공).

    Returns:
        TagApplicationResult.

    Idempotent 동작:
        - 기존 ``CADOpt_F8_*`` tag만 제거 후 새 tier tag 부여
        - 비-F8 tag 보존
        - 새 tier가 Keep이면 F8 tag 0개 (implicit Keep)
        - 변경이 없으면 ``actor.modify()`` 호출 생략 (성능 + undo buffer 절약)

    Note:
        모듈은 ``unreal`` import 0. Actor 객체는 duck-typed로 처리
        (``tags`` / ``modify`` / ``is_valid`` / ``get_path_name`` 등).
    """
    measurements = report.measurements
    total = len(measurements)
    tiers = compute_tiers_for_report(report, threshold_cm)

    # F5 nx_category — CSV row용. compute_tiers_for_report 내부에서도 한 번
    # 호출하지만 결과 폐기됨. 단일 차량 측정에서 두 번 classify는 작은 비용
    # (~ms)이라 허용. 최적화는 Phase 2.
    from cad_optimizer.nx_naming import classify_measurements
    categories = classify_measurements(measurements)

    tagged = 0
    implicit_keep = 0
    not_found = 0
    csv_rows: List[List] = []

    for i, (m, tier, nx_cat) in enumerate(zip(measurements, tiers, categories)):
        if progress_callback is not None:
            try:
                cont = progress_callback(i, total, f"F8 tag {i + 1}/{total}")
            except Exception:
                cont = True
            if cont is False:  # explicit False (None은 진행 가정)
                break

        actor = m.actor
        if not _actor_is_usable(actor):
            not_found += 1
            continue

        # CSV 박제 (모든 actor — implicit Keep 포함)
        csv_rows.append([
            _safe_path(actor),
            _safe_label(actor),
            f"{m.bbox_diagonal_cm:.3f}",
            nx_cat,
            m.override_status,
            tier,
        ])

        # Idempotent tag write
        # target_f8 = 부여할 F8 tag 리스트 (Keep tier면 빈 리스트)
        target_f8 = [] if tier == TIER_KEEP else [tier]
        try:
            current_tags = list(actor.tags)
        except Exception:
            not_found += 1
            continue

        current_f8 = [
            str(t) for t in current_tags if str(t).startswith(TAG_PREFIX)
        ]

        if current_f8 != target_f8:
            # 변경 필요. 비-F8 보존 + target_f8 부여.
            try:
                if hasattr(actor, "modify"):
                    actor.modify()
                preserved = [
                    str(t) for t in current_tags
                    if not str(t).startswith(TAG_PREFIX)
                ]
                actor.tags = preserved + target_f8
            except Exception:
                # 보호된 actor 등 — silent skip, not_found 카운트
                not_found += 1
                continue
        # else: already correct, no write needed (idempotent fast path)

        # Final state 카운트 (이 actor의 최종 F8 tag 유무 기준)
        if target_f8:
            tagged += 1
        else:
            implicit_keep += 1

    csv_path_str = ""
    if csv_out_path:
        _write_csv(
            csv_out_path,
            csv_rows,
            total=total,
            tagged=tagged,
            implicit_keep=implicit_keep,
            not_found=not_found,
            threshold_cm=threshold_cm,
            plugin_commit=plugin_commit,
        )
        csv_path_str = csv_out_path.replace("\\", "/")

    tier_counts_dict = dict(count_tiers(tiers))
    return TagApplicationResult(
        total_actors=total,
        tagged=tagged,
        implicit_keep=implicit_keep,
        tier_counts=tier_counts_dict,
        not_found_in_level=not_found,
        csv_path=csv_path_str,
    )


# ─── CSV 박제 (4-line comment header + column header + rows) ────────


def _write_csv(
    path: str,
    rows: List[List],
    total: int,
    tagged: int,
    implicit_keep: int,
    not_found: int,
    threshold_cm: float,
    plugin_commit: str,
) -> None:
    """F8 metadata CSV 박제. F4/F6 CSV 패턴 일관 (# 주석 4줄 + writer header)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_str = plugin_commit if plugin_commit else "(미지정)"
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(f"# F8 Metadata Tags — generated {ts}\n")
        f.write(f"# Plugin commit: {commit_str}\n")
        f.write(f"# Threshold (Tiny preset): {threshold_cm:.2f} cm\n")
        f.write(
            f"# Total: {total} "
            f"(tagged: {tagged}, implicit_keep: {implicit_keep}, "
            f"not_found: {not_found})\n"
        )
        writer = csv_mod.writer(f)
        writer.writerow([
            "actor_path",
            "actor_label",
            "diagonal_cm",
            "nx_category",
            "override_status",
            "tier",
        ])
        for row in rows:
            writer.writerow(row)
