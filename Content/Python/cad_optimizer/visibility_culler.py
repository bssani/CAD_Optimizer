"""Visibility Culler — Phase 3 첫 task.

F8 metadata tag (``CADOpt_F8_Cull_High``, ``CADOpt_F8_Cull_Mid``) 보유 actor를
영구 hidden 처리 (`set_actor_hidden_in_game(True)`).

설계 원칙 (F8 / Phase 2 패턴 재사용):
- Module 자체엔 ``import unreal`` 0. Actor 객체 duck-typed (``tags``,
  ``modify``, ``set_actor_hidden_in_game``, ``hidden_in_game`` 등).
- F-pattern: 분류 (`find_cull_targets`) + 적용 (`apply_visibility_culling`)
  같은 모듈에서 (단순 mutation). Caller (panel.py) 가 ScopedSlowTask wrap.
- Idempotent: 이미 hidden 인 actor 재실행 시 skip (modify() 호출 안 함).
- Reversible: ``actor.modify()`` 호출 후 set → UE undo 가능. 또는
  ``run_restore_visibility`` 로 sentinel tag 기반 일괄 복원.

대상 정의:
- F8 Cull_High = small AND slot_empty AND nx_category ∈ {LATCH, BRACKET}
- F8 Cull_Mid = small AND slot_empty (그 외 카테고리)
- Review / Keep tier 는 대상 아님 (사용자 재검토 필요 / 보존)

Sentinel tag (Phase 2 패턴):
- ``CADOpt_P3_Hidden`` — 박제/감사용 (어떤 actor가 P3 culler가 hidden 시켰는지)
- ``CADOpt_P3_Source_<tier>`` — 어떤 F8 tier 가 근거였는지 추적

박제 reference:
- ``docs/measurements/integrated_report_c1yc_2_mcm.md`` §8/§12 — F8 tier schema
- ``docs/measurements/f8_c1yc_2_mcm.md`` — F8 tier 분포 실측
- ``docs/measurements/actor_merging_c1yc_2_mcm.md`` — Phase 2 머지 결과

Out of scope (이 모듈):
- 동적 cull (매 frame 토글) — UE 자체 GPU cull 신뢰
- Cull Distance Volume — 자동차 PCVR 시나리오에 효과 거의 0
- Scene/layer 기반 visibility (도어 열림/닫힘 등) — 게임 로직 영역
"""
from __future__ import annotations

import csv as csv_mod
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional


# F8 tier 상수 (metadata_tagger 와 중복 정의 회피 위해 string literal).
# Cull_High = 가장 확신 높은 cull 후보, Cull_Mid = 차순위 후보.
TIER_CULL_HIGH = "CADOpt_F8_Cull_High"
TIER_CULL_MID = "CADOpt_F8_Cull_Mid"
DEFAULT_TARGET_TIERS = frozenset({TIER_CULL_HIGH, TIER_CULL_MID})

# Phase 3 sentinel tag prefix. Phase 2 (CADOpt_P2_*) 와 구분.
TAG_PREFIX = "CADOpt_P3_"
TAG_HIDDEN = "CADOpt_P3_Hidden"


@dataclass
class CullResult:
    """Visibility culling 결과 — Output Log + CSV 박제 입력."""

    target_count: int = 0          # F8 tag 보유 actor 중 target_tiers 매치 수
    newly_hidden: int = 0          # set_actor_hidden_in_game(True) 호출 성공
    already_hidden: int = 0        # 재실행 시 이미 hidden (no-op)
    skipped: int = 0               # invalid actor / API 실패
    tier_breakdown: Dict[str, int] = field(default_factory=dict)
    csv_path: str = ""


# ─── Actor-side helpers (duck-typed, ``unreal`` 의존 0) ─────────────


def _actor_is_usable(actor) -> bool:
    if actor is None:
        return False
    if hasattr(actor, "is_valid"):
        try:
            return bool(actor.is_valid())
        except Exception:
            return False
    return True


def _safe_tags(actor) -> List[str]:
    try:
        return [str(t) for t in (actor.tags or [])]
    except Exception:
        return []


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


def _is_hidden_in_game(actor) -> bool:
    """현재 hidden_in_game 상태. property 우선, fallback to editor_property."""
    try:
        if hasattr(actor, "hidden_in_game"):
            return bool(actor.hidden_in_game)
    except Exception:
        pass
    try:
        return bool(actor.get_editor_property("hidden_in_game"))
    except Exception:
        return False


# ─── Pure-ish: target selection ─────────────────────────────────────


def find_cull_targets(
    actors: list,
    target_tiers: frozenset = DEFAULT_TARGET_TIERS,
) -> List:
    """Actor 중 ``target_tiers`` 에 매치되는 F8 tag 보유 actor 만 반환.

    Phase 2 머지 이후 호출 시 머지된 source actor 는 사라졌으므로 결과는
    "머지에서 살아남은 F8 tag actor" 이 됨 — Phase 3 실 cull 대상.
    """
    targets: List = []
    for actor in actors:
        if not _actor_is_usable(actor):
            continue
        tags = _safe_tags(actor)
        if any(t in target_tiers for t in tags):
            targets.append(actor)
    return targets


def _matched_tier(actor, target_tiers: frozenset) -> str:
    """Actor의 F8 tag 중 target_tiers 매치되는 첫 번째 (sentinel tag 용)."""
    for t in _safe_tags(actor):
        if t in target_tiers:
            return t
    return ""


# ─── Mutation: apply ─────────────────────────────────────────────────


def apply_visibility_culling(
    actors: list,
    target_tiers: frozenset = DEFAULT_TARGET_TIERS,
    csv_out_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], bool]] = None,
    plugin_commit: str = "",
) -> CullResult:
    """F8 tag 보유 actor 를 영구 hidden 처리. Idempotent.

    Args:
        actors: ``EditorActorSubsystem.get_all_level_actors()`` 결과.
        target_tiers: cull 대상 F8 tier set (default High + Mid).
        csv_out_path: 박제 CSV. None이면 write 생략.
        progress_callback: ``(current, total, msg) -> bool``. False 반환 시 중단.
        plugin_commit: CSV 헤더에 박제할 commit hash.

    Returns:
        CullResult — Output Log 입력.

    Idempotent:
        - 이미 hidden_in_game = True 인 actor → no-op (already_hidden 카운트)
        - 변경 필요한 actor → ``actor.modify()`` + ``set_actor_hidden_in_game(True)``
          + sentinel tag 부여 (기존 P3 tag 제거 후 재부여)
    """
    targets = find_cull_targets(actors, target_tiers)
    result = CullResult(target_count=len(targets))
    csv_rows: List[List] = []

    for i, actor in enumerate(targets):
        if progress_callback is not None:
            try:
                cont = progress_callback(
                    i, len(targets),
                    f"P3 cull {i + 1}/{len(targets)}"
                )
            except Exception:
                cont = True
            if cont is False:
                break

        if not _actor_is_usable(actor):
            result.skipped += 1
            continue

        tier = _matched_tier(actor, target_tiers)
        result.tier_breakdown[tier] = result.tier_breakdown.get(tier, 0) + 1
        was_hidden = _is_hidden_in_game(actor)
        action = ""

        if was_hidden:
            result.already_hidden += 1
            action = "skip (already hidden)"
            # Sentinel tag 보강만 (없으면 부여, 있으면 그대로)
            try:
                tags = _safe_tags(actor)
                if TAG_HIDDEN not in tags:
                    if hasattr(actor, "modify"):
                        actor.modify()
                    actor.tags = tags + [TAG_HIDDEN, f"CADOpt_P3_Source_{tier}"]
                    action = "skip-tag-added"
            except Exception:
                result.skipped += 1
                action = "tag-fail"
        else:
            try:
                if hasattr(actor, "modify"):
                    actor.modify()
                actor.set_actor_hidden_in_game(True)
                # Sentinel tag — 기존 P3 tag 제거 후 재부여.
                tags = _safe_tags(actor)
                preserved = [t for t in tags if not t.startswith(TAG_PREFIX)]
                actor.tags = preserved + [
                    TAG_HIDDEN,
                    f"CADOpt_P3_Source_{tier}",
                ]
                result.newly_hidden += 1
                action = "hidden"
            except Exception:
                result.skipped += 1
                action = "fail"
                continue

        csv_rows.append([
            _safe_path(actor),
            _safe_label(actor),
            tier,
            "True" if was_hidden else "False",
            action,
        ])

    if csv_out_path:
        _write_csv(
            csv_out_path, csv_rows, result, plugin_commit,
            target_tiers=target_tiers,
        )
        result.csv_path = csv_out_path.replace("\\", "/")

    return result


def restore_visibility_by_tag(
    actors: list,
    progress_callback: Optional[Callable[[int, int, str], bool]] = None,
) -> Dict[str, int]:
    """Phase 3 sentinel tag (``CADOpt_P3_Hidden``) 보유 actor 일괄 복원.

    Use case: cull 결과 review 중 잘못된 hide 발견 시 일괄 revert.
    UE undo 가 transaction 단위라 부분 revert 어려운 경우 대안.

    Returns:
        ``{"restored": N, "skipped": N}`` 카운트.
    """
    restored = 0
    skipped = 0
    p3_actors = [
        a for a in actors
        if _actor_is_usable(a) and TAG_HIDDEN in _safe_tags(a)
    ]
    for i, actor in enumerate(p3_actors):
        if progress_callback is not None:
            try:
                cont = progress_callback(
                    i, len(p3_actors),
                    f"P3 restore {i + 1}/{len(p3_actors)}"
                )
            except Exception:
                cont = True
            if cont is False:
                break
        try:
            if hasattr(actor, "modify"):
                actor.modify()
            actor.set_actor_hidden_in_game(False)
            tags = _safe_tags(actor)
            preserved = [t for t in tags if not t.startswith(TAG_PREFIX)]
            actor.tags = preserved
            restored += 1
        except Exception:
            skipped += 1
    return {"restored": restored, "skipped": skipped}


# ─── CSV 박제 (F4/F6/F8 패턴 일관) ──────────────────────────────────


def _write_csv(
    path: str,
    rows: List[List],
    result: CullResult,
    plugin_commit: str,
    target_tiers: frozenset,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_str = plugin_commit if plugin_commit else "(미지정)"
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    tier_str = ", ".join(sorted(target_tiers))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(f"# Phase 3 Visibility Culling — generated {ts}\n")
        f.write(f"# Plugin commit: {commit_str}\n")
        f.write(f"# Target tiers: {tier_str}\n")
        f.write(
            f"# Targets: {result.target_count} "
            f"(newly hidden: {result.newly_hidden}, "
            f"already hidden: {result.already_hidden}, "
            f"skipped: {result.skipped})\n"
        )
        writer = csv_mod.writer(f)
        writer.writerow([
            "actor_path",
            "actor_label",
            "matched_tier",
            "was_hidden_before",
            "action",
        ])
        for row in rows:
            writer.writerow(row)
