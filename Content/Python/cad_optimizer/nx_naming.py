"""NX naming classification — F5.

Pure classifier. Maps a CAD part label (typically the immediate attach
parent label captured by F4) to one of 8 GM-internal categories or
"UNCATEGORIZED".

Patterns derived from C1YC_2_MCM analysis (45,805 labels) — see
``docs/concepts/nx_naming_patterns.md`` for the derivation, frequency
tables, and known limitations.

Notes:
    - V2 regex uses explicit ``[_\\-]`` boundaries instead of Python's
      ``\\b`` word boundary, because ``\\w`` includes underscore — so
      ``\\b`` does not break on ``_LATCH_`` style tokens.
    - Match priority is top-to-bottom in ``NX_CATEGORY_PATTERNS``.
      LATCH/VALVE/etc. take precedence over ASSEMBLY so that
      ``LATCH_ASM-R_SEAT`` resolves to LATCH, not ASSEMBLY.
    - UNCATEGORIZED ceiling (~22.91% on C1YC_2_MCM) is dominated by
      supplier serial numbers with no English keywords. Recovering
      those needs ERP/PLM lookup — see Phase 2 backlog item #1.
"""
from __future__ import annotations

import re
from collections import Counter, OrderedDict
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from cad_optimizer.small_part_detector import SmallPartMeasurement


# 박제: docs/concepts/nx_naming_patterns.md Section 4 (Phase 1 V2 — 최종)
# 글자 단위 일치. 차이 발생 시 박제 우선 — 별도 patch task.
# 우선순위: 위→아래 첫 매칭에서 stop. ASSEMBLY는 마지막.
NX_CATEGORY_PATTERNS: "OrderedDict[str, re.Pattern]" = OrderedDict([
    ("FASTENER", re.compile(r'(?:^|[_\-])(BOLT|NUT|SCREW|CLIP|WASHER|RIVET)(?=[_\-]|$)', re.IGNORECASE)),
    ("VALVE",    re.compile(r'(?:^|[_\-])(VALVE|PMP)(?=[_\-]|$)', re.IGNORECASE)),
    ("LATCH",    re.compile(r'(?:^|[_\-])(LATCH|LOCK|HINGE)(?=[_\-]|$)', re.IGNORECASE)),
    ("BRACKET",  re.compile(r'(?:^|[_\-])(BRKT|BRACKET|SUPPORT|REINF|REINFORCEMENT)(?=[_\-]|$)', re.IGNORECASE)),
    ("HOUSING",  re.compile(r'(?:^|[_\-])(MODULE|HOUSING|CASE|CSE|ENCLOSURE)(?=[_\-]|$)', re.IGNORECASE)),
    ("TRIM",     re.compile(r'(?:^|[_\-])(SHUTTER|TRIM|COVER|SEAL|MOLDING|FASCIA|BACKING)(?=[_\-]|$)', re.IGNORECASE)),
    ("WIRING",   re.compile(r'(?:^|[_\-])(WRG|HARNESS|CABLE|WIRING)(?=[_\-]|$)', re.IGNORECASE)),
    ("ASSEMBLY", re.compile(r'_ASM[-_]', re.IGNORECASE)),  # last — drops to UNCATEGORIZED if no match
])

UNCATEGORIZED = "UNCATEGORIZED"

# 결과 보고 시 일관된 카테고리 순서 (FASTENER ... ASSEMBLY UNCATEGORIZED).
NX_CATEGORY_ORDER: List[str] = list(NX_CATEGORY_PATTERNS.keys()) + [UNCATEGORIZED]


def classify_label(label: str) -> str:
    """Map a part label to its NX category.

    Args:
        label: typically ``SmallPartMeasurement.parent_part_label``.
            Empty string (root-level mesh) classifies as UNCATEGORIZED.

    Returns:
        Category name from ``NX_CATEGORY_PATTERNS`` keys, or
        ``UNCATEGORIZED`` if no pattern matches.

    Future hook (Phase 2 backlog #1):
        ERP/PLM supplier-code lookup falls in here as a fallback when
        keyword regex returns UNCATEGORIZED. Not implemented in Phase 1.
    """
    if not label:
        return UNCATEGORIZED
    for category, pattern in NX_CATEGORY_PATTERNS.items():
        if pattern.search(label):
            return category
    return UNCATEGORIZED


def classify_measurements(
    measurements: List["SmallPartMeasurement"],
) -> List[str]:
    """Classify each measurement's parent_part_label.

    Returns parallel list of category strings — same length as
    ``measurements``, same order. Caller zips with measurements for
    CSV writing.
    """
    return [classify_label(m.parent_part_label) for m in measurements]


def category_counts(
    categories: List[str],
) -> "OrderedDict[str, int]":
    """Count categories in canonical order (NX_CATEGORY_ORDER).

    Empty/missing categories present with count 0 — predictable Output
    Log layout regardless of which categories actually appear.
    """
    raw = Counter(categories)
    return OrderedDict((cat, raw.get(cat, 0)) for cat in NX_CATEGORY_ORDER)
