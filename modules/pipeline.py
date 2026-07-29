from __future__ import annotations
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import httpx

from modules.config import REQUEST_TIMEOUT
from modules.cv_analysis import analyze_image
from modules.ai_analysis import analyze_subjective
from modules.logo_matcher import load_reference_logos, check_logo
from modules.brand_rules import evaluate_objective_rules
from modules.scoring import compute_total_score

try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except Exception:
    add_script_run_ctx = None
    get_script_run_ctx = None

ProgressCb = Callable[[str], None]


def _noop(_msg: str) -> None:
    return None


def _safe(cb: ProgressCb) -> ProgressCb:
    """Wrap the progress callback so failures inside worker threads never bubble."""
    def _wrapped(msg: str) -> None:
        try:
            cb(msg)
        except Exception:
            pass
    return _wrapped


def _thread_init(ctx) -> None:
    """Runs once per worker thread BEFORE any task, so `st.*` calls are safe."""
    if add_script_run_ctx is not None and ctx is not None:
        try:
            add_script_run_ctx(threading.current_thread(), ctx)
        except Exception:
            pass


def analyze_one_image(image_path: str | Path, kv_type: str,
                      client: httpx.Client,
                      progress_cb: ProgressCb = _noop,
                      ctx=None) -> dict:
    """
    Within-image parallelism:
      1. Vision runs first (subjective needs its output).
      2. Then subjective + N logo checks run concurrently.
    """
    progress_cb = _safe(progress_cb)
    name = Path(image_path).name
    progress_cb(f"Vision: {name}…")
    cv = analyze_image(image_path, client=client)

    refs = load_reference_logos()
    subj = None
    matches: list[dict] = []

    max_workers = 1 + (len(refs) if refs else 0)
    with ThreadPoolExecutor(max_workers=max(2, min(12, max_workers)),
                            initializer=_thread_init, initargs=(ctx,),
                            thread_name_prefix=f"inner-{name}") as pool:
        futs = {pool.submit(analyze_subjective, image_path, cv, kv_type, client): "subj"}
        for ref in refs or []:
            futs[pool.submit(check_logo, image_path, ref, client)] = ("logo", ref)

        progress_cb(f"Gemini (subjetivo + {len(refs or [])} logos): {name}…")

        for fut in as_completed(futs):
            tag = futs[fut]
            try:
                res = fut.result()
            except Exception:
                res = None
            if tag == "subj":
                subj = res or {"results": [], "overall_impression": ""}
            elif isinstance(tag, tuple) and tag[0] == "logo" and res:
                matches.append(res)

    cv["reference_matches"] = matches

    # Bring Gemini's area estimates into cv so objective rules can use them.
    if subj:
        areas = subj.get("area_estimates") or {}
        if cv.get("dominant_area") is None and areas.get("photo_area_pct") is not None:
            cv["dominant_area"] = areas["photo_area_pct"]
        if cv.get("offer_area") is None and areas.get("offer_area_pct") is not None:
            cv["offer_area"] = areas["offer_area_pct"]
        if cv.get("additional_area") is None and areas.get("propuesta_area_pct") is not None:
            cv["additional_area"] = areas["propuesta_area_pct"]

    obj_results = evaluate_objective_rules(cv, kv_type)
    score = compute_total_score(obj_results, subj)

    return {
        "name": name,
        "path": str(image_path),
        "kv_type": kv_type,
        "cv": cv,
        "obj_results": obj_results,
        "subj_data": subj,
        "score": score,
    }


def analyze_images(image_paths: list[str], kv_types: list[str],
                   progress_cb: ProgressCb = _noop,
                   max_parallel_images: int = 4) -> list[dict]:
    """Cross-image parallelism with Streamlit context propagated to workers."""
    assert len(image_paths) == len(kv_types)
    total = len(image_paths)
    results: list[dict | None] = [None] * total

    progress_cb = _safe(progress_cb)
    ctx = get_script_run_ctx() if get_script_run_ctx else None

    def _worker(idx: int, path: str, kv_type: str, client: httpx.Client) -> tuple[int, dict]:
        try:
            r = analyze_one_image(path, kv_type, client, progress_cb, ctx=ctx)
        except Exception as e:
            r = {"name": Path(path).name, "path": path, "kv_type": kv_type, "error": str(e)}
        return idx, r

    with httpx.Client(timeout=REQUEST_TIMEOUT, http2=False) as client:
        workers = max(1, min(max_parallel_images, total))
        with ThreadPoolExecutor(max_workers=workers,
                                initializer=_thread_init, initargs=(ctx,),
                                thread_name_prefix="outer") as pool:
            futs = [
                pool.submit(_worker, i, p, t, client)
                for i, (p, t) in enumerate(zip(image_paths, kv_types))
            ]
            done = 0
            for fut in as_completed(futs):
                idx, r = fut.result()
                results[idx] = r
                done += 1
                progress_cb(f"[{done}/{total}] Listo: {r.get('name','')}")

    return [r for r in results if r is not None]


analyze_images_parallel = analyze_images
