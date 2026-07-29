from __future__ import annotations
from typing import Iterable

STATUS_VALUE = {"pass": 1.0, "partial": 0.5, "fail": 0.0}


def objective_pct(obj_results: Iterable[dict]) -> tuple[float, float]:
    """Returns (weighted_score, total_weight) as fractions of 1.0."""
    total_w = 0.0
    got = 0.0
    for r in obj_results:
        w = float(r.get("weight") or 1)
        v = STATUS_VALUE.get(r.get("status", "fail"), 0.0)
        total_w += w
        got += w * v
    return (got / total_w if total_w else 0.0), total_w


def subjective_pct(subj_results: Iterable[dict]) -> tuple[float, float]:
    total_w = 0.0
    got = 0.0
    for r in subj_results:
        score = r.get("score")
        if score is None:
            continue
        w = float(r.get("weight") or 1)
        total_w += w
        got += w * (float(score) / 5.0)
    return (got / total_w if total_w else 0.0), total_w


def compute_total_score(obj_results: list[dict],
                        subj_data: dict | None,
                        abcd_data: list[dict] | None = None) -> dict:
    obj_pct, obj_w = objective_pct(obj_results or [])
    subj_pct, subj_w = subjective_pct((subj_data or {}).get("results") or [])
    abcd_pct, abcd_w = subjective_pct(abcd_data or [])

    has_obj = obj_w > 0
    has_subj = subj_w > 0
    has_abcd = abcd_w > 0

    if has_abcd:
        # Video: 40/30/30 (or fallback to what's present)
        parts = []
        if has_obj:
            parts.append(("obj", obj_pct, 0.40))
        if has_subj:
            parts.append(("subj", subj_pct, 0.30))
        parts.append(("abcd", abcd_pct, 0.30))
    else:
        # Image: 50/50
        parts = []
        if has_obj:
            parts.append(("obj", obj_pct, 0.50))
        if has_subj:
            parts.append(("subj", subj_pct, 0.50))
        if not parts and has_abcd:
            parts.append(("abcd", abcd_pct, 1.0))

    if not parts:
        return {"total_pct": 0.0, "obj_pct": obj_pct, "subj_pct": subj_pct,
                "abcd_pct": abcd_pct, "weights": {}}

    total_w = sum(w for _, _, w in parts)
    total = sum(p * (w / total_w) for _, p, w in parts)
    return {
        "total_pct": total,
        "obj_pct": obj_pct,
        "subj_pct": subj_pct,
        "abcd_pct": abcd_pct,
        "weights": {name: w / total_w for name, _, w in parts},
    }
