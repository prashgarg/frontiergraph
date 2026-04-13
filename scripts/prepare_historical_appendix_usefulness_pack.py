from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.learned_reranker import FEATURE_FAMILIES, fit_glm_logit_reranker, fit_pairwise_logit_reranker, score_with_reranker
from src.analysis.ranking_utils import pref_attach_ranking_from_universe
from src.research_allocation_v2 import _aggregate_support
from src.utils import load_corpus


SYSTEM_PROMPT = """You are rating candidate research-question objects for current reader usefulness.

Judge only what is visible in the supplied record. Do not use outside knowledge, web search, topic prestige, publication prospects, or whether the candidate was later pursued in the literature.

The record may describe one of two graph-grounded research-question objects:

- a path-supported missing direct relation
- an existing direct relation with a proposed missing channel

Judge the rendered question object first. Use the graph fields only to understand what the object is trying to say.

If a bridge or path is shown, it is an intervening concept from the literature graph. It is not necessarily a proven mechanism. It may represent a mechanism, channel, condition, policy lever, or other bridge.

You are not judging novelty, importance, truth, or likely future success.
You are judging only whether the item reads as a useful, intelligible research-question object to a current human reader.

Rate:
- readability: is the wording easy to read and parse?
- interpretability: can a reader tell what relationship or bridge is being proposed?
- usefulness: is this a usable research-question object, even if it may still need revision?
- artifact_risk: does it read like a graph artifact rather than a real research question?

Score anchors:
- 5 = clear and strong
- 3 = understandable but mixed
- 1 = weak or unclear

artifact_risk anchors:
- low = reads like a normal research question
- medium = partly usable but somewhat artificial, generic, or awkward
- high = mostly reads like a graph artifact or malformed question object

Return JSON only.
Keep the reason under 18 words.
Be concise and evidence-based."""


USER_TEMPLATE = """Evaluate this candidate for current reader usefulness only.

JSON record:
{record_json}"""


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "item_id": {"type": "string"},
        "readability": {"type": "integer", "minimum": 1, "maximum": 5},
        "interpretability": {"type": "integer", "minimum": 1, "maximum": 5},
        "usefulness": {"type": "integer", "minimum": 1, "maximum": 5},
        "artifact_risk": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "reason": {"type": "string", "maxLength": 100},
    },
    "required": [
        "item_id",
        "readability",
        "interpretability",
        "usefulness",
        "artifact_risk",
        "reason",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the full historical appendix usefulness LLM pack.")
    parser.add_argument(
        "--panel",
        default="outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet",
        dest="panel_path",
    )
    parser.add_argument(
        "--manifest",
        default="outputs/paper/123_effective_benchmark_widened_1990_2015/manifest.json",
        dest="manifest_path",
    )
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument(
        "--adopted-configs",
        default="outputs/paper/83_quality_confirm_path_to_direct_effective/adopted_surface_backtest_configs.csv",
        dest="adopted_configs_path",
    )
    parser.add_argument("--arms", default="adopted,transparent,pref_attach")
    parser.add_argument("--top-k", type=int, default=250, dest="top_k")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--max-output-tokens", type=int, default=120, dest="max_output_tokens")
    parser.add_argument("--reasoning-effort", default="none", dest="reasoning_effort")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--family-mode",
        default="auto",
        choices=["auto", "path_to_direct", "direct_to_path"],
        dest="family_mode",
        help="Override the candidate-family mode used in the LLM-facing record.",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/124_historical_appendix_usefulness_pack",
        dest="out_dir",
    )
    return parser.parse_args()


def _load_adopted_configs(path: Path) -> dict[int, dict[str, Any]]:
    df = pd.read_csv(path)
    out: dict[int, dict[str, Any]] = {}
    for row in df.itertuples(index=False):
        out[int(row.horizon)] = {
            "model_kind": str(row.model_kind),
            "feature_family": str(row.feature_family),
            "alpha": float(row.alpha),
        }
    return out


def _fit_model(
    train_rows: pd.DataFrame,
    model_kind: str,
    feature_family: str,
    alpha: float,
    seed: int,
) -> Any | None:
    feature_names = [c for c in FEATURE_FAMILIES[str(feature_family)] if c in train_rows.columns]
    if not feature_names:
        return None
    if str(model_kind) == "glm_logit":
        return fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=float(alpha))
    if str(model_kind) == "pairwise_logit":
        return fit_pairwise_logit_reranker(
            train_rows,
            feature_names=feature_names,
            alpha=float(alpha),
            negatives_per_positive=2,
            max_pairs_per_cutoff=2000,
            seed=int(seed),
        )
    raise ValueError(f"Unsupported model kind: {model_kind}")


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _build_code_label_map(corpus_df: pd.DataFrame) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for code_col, label_col in [("src_code", "src_label"), ("dst_code", "dst_label")]:
        if code_col not in corpus_df.columns or label_col not in corpus_df.columns:
            continue
        sub = corpus_df[[code_col, label_col]].dropna().drop_duplicates()
        for row in sub.itertuples(index=False):
            code = _clean_text(getattr(row, code_col))
            label = _clean_text(getattr(row, label_col))
            if code and label and code not in label_map:
                label_map[code] = label
    return label_map


def _json_list(value: Any) -> list[Any]:
    text = _clean_text(value)
    if not text or text in {"[]", "{}", "nan", "None"}:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _label_for(code_or_label: Any, label_map: dict[str, str]) -> str:
    value = _clean_text(code_or_label)
    return _clean_text(label_map.get(value, value))


def _family_mode_for_row(row: pd.Series, args: argparse.Namespace) -> str:
    if str(args.family_mode) != "auto":
        return str(args.family_mode)
    for col in ["candidate_family_mode", "candidate_family_mode_input"]:
        value = _clean_text(row.get(col, ""))
        if value:
            return value
    return "path_to_direct"


def _relation_text(source: str, target: str) -> str:
    if source and target:
        return f"{source} -> {target}"
    return source or target


def _path_text(source: str, bridge: str, target: str) -> str:
    if source and bridge and target:
        return f"{source} -> {bridge} -> {target}"
    return _relation_text(source, target)


def _render_labeled_path(path: list[Any], label_map: dict[str, str]) -> str:
    labels = [_label_for(item, label_map) for item in path if _clean_text(item)]
    labels = [label for label in labels if label]
    return " -> ".join(labels)


def _best_existing_support_path(row: pd.Series, label_map: dict[str, str]) -> str:
    paths = _json_list(row.get("top_paths_json"))
    if not paths:
        source = _label_for(row.get("source_label", ""), label_map)
        bridge = _label_for(row.get("focal_mediator_label", ""), label_map)
        target = _label_for(row.get("target_label", ""), label_map)
        return _path_text(source, bridge, target) if bridge else ""
    best = paths[0]
    if isinstance(best, dict):
        path = best.get("path", [])
        rendered = _render_labeled_path(path if isinstance(path, list) else [], label_map)
        if rendered:
            return rendered
    return ""


def _support_cache_for_cutoffs(
    corpus_df: pd.DataFrame,
    cutoff_years: list[int],
    max_neighbors: int = 40,
) -> dict[int, dict[str, Any]]:
    cache: dict[int, dict[str, Any]] = {}
    for cutoff_t in sorted({int(x) for x in cutoff_years}):
        train_df = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
        payload = _aggregate_support(train_df)
        support_edges = payload["support_edges"].copy()
        out_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
        in_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
        if not support_edges.empty:
            for row in support_edges.itertuples(index=False):
                src = _clean_text(getattr(row, "src_code"))
                dst = _clean_text(getattr(row, "dst_code"))
                w = float(getattr(row, "edge_weight", 0.0) or 0.0)
                if src and dst and src != dst:
                    out_map[src].append((dst, w))
                    in_map[dst].append((src, w))
            out_map = {
                key: sorted(vals, key=lambda item: item[1], reverse=True)[:max_neighbors]
                for key, vals in out_map.items()
            }
            in_map = {
                key: sorted(vals, key=lambda item: item[1], reverse=True)[:max_neighbors]
                for key, vals in in_map.items()
            }
        cache[int(cutoff_t)] = {"out_map": out_map, "in_map": in_map}
    return cache


def _find_short_support_path(
    source: str,
    target: str,
    out_map: dict[str, list[tuple[str, float]]],
    max_edges: int = 4,
    branch_cap: int = 12,
) -> list[str]:
    source = _clean_text(source)
    target = _clean_text(target)
    if not source or not target:
        return []
    queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
    while queue:
        node, path = queue.popleft()
        if len(path) - 1 >= max_edges:
            continue
        for nxt, _weight in out_map.get(node, [])[:branch_cap]:
            if nxt in path:
                continue
            new_path = path + [nxt]
            if nxt == target and len(new_path) >= 3:
                return new_path
            queue.append((nxt, new_path))
    return []


def _best_one_sided_bridge(
    source: str,
    target: str,
    out_map: dict[str, list[tuple[str, float]]],
    in_map: dict[str, list[tuple[str, float]]],
) -> tuple[str, str]:
    source = _clean_text(source)
    target = _clean_text(target)
    source_side = [(node, float(weight)) for node, weight in out_map.get(source, []) if _clean_text(node) and _clean_text(node) != target]
    target_side = [(node, float(weight)) for node, weight in in_map.get(target, []) if _clean_text(node) and _clean_text(node) != source]
    best_source = source_side[0] if source_side else ("", 0.0)
    best_target = target_side[0] if target_side else ("", 0.0)
    if best_source[1] >= best_target[1] and _clean_text(best_source[0]):
        return _clean_text(best_source[0]), "source_side"
    if _clean_text(best_target[0]):
        return _clean_text(best_target[0]), "target_side"
    return "", ""


def _augment_question_objects(
    selected_df: pd.DataFrame,
    corpus_df: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    if selected_df.empty:
        return selected_df.copy()
    out = selected_df.copy()
    label_map = _build_code_label_map(corpus_df)
    cutoff_years = sorted({int(x) for x in out["cutoff_year_t"].dropna().astype(int).unique()}) if "cutoff_year_t" in out.columns else []
    support_cache = _support_cache_for_cutoffs(corpus_df, cutoff_years) if cutoff_years else {}

    question_render_col: list[str] = []
    supporting_path_col: list[str] = []
    direct_relation_col: list[str] = []
    proposed_path_col: list[str] = []
    construction_note_col: list[str] = []

    for row in out.itertuples(index=False):
        row_s = pd.Series(row._asdict())
        family_mode = _family_mode_for_row(row_s, args)
        source_label = _label_for(getattr(row, "source_label", ""), label_map)
        target_label = _label_for(getattr(row, "target_label", ""), label_map)
        direct_relation = _relation_text(source_label, target_label)

        if family_mode == "direct_to_path":
            cache = support_cache.get(int(getattr(row, "cutoff_year_t", 0)), {"out_map": {}, "in_map": {}})
            out_map = cache.get("out_map", {})
            in_map = cache.get("in_map", {})
            proposed_codes = _find_short_support_path(
                source=str(getattr(row, "u", "")),
                target=str(getattr(row, "v", "")),
                out_map=out_map,
                max_edges=4,
                branch_cap=12,
            )
            if proposed_codes:
                proposed_path = _render_labeled_path(proposed_codes, label_map)
                if len(proposed_codes) == 3:
                    bridge_label = _label_for(proposed_codes[1], label_map)
                    question_render = f"Could {source_label} affect {target_label} through {bridge_label}?"
                else:
                    bridge_phrase = ", ".join(_label_for(code, label_map) for code in proposed_codes[1:-1])
                    question_render = f"Could {source_label} affect {target_label} through the pathway {bridge_phrase}?"
                construction_note = "The direct relation is already present. The proposed path is inferred from the surrounding support neighborhood and is not yet established as a full observed path."
            else:
                bridge_code, side = _best_one_sided_bridge(
                    source=str(getattr(row, "u", "")),
                    target=str(getattr(row, "v", "")),
                    out_map=out_map,
                    in_map=in_map,
                )
                bridge_label = _label_for(bridge_code, label_map)
                proposed_path = _path_text(source_label, bridge_label, target_label) if bridge_label else ""
                if bridge_label:
                    question_render = f"Could {source_label} affect {target_label} through {bridge_label}?"
                    construction_note = (
                        "The direct relation is already present. The bridge is inferred from a one-sided local support neighborhood, so it should be read as a candidate channel rather than an established pathway."
                        if side else
                        "The direct relation is already present. The bridge is a candidate channel rather than an established pathway."
                    )
                else:
                    question_render = f"What missing channel could connect {source_label} to {target_label}?"
                    construction_note = "The direct relation is already present, but the local graph does not yet give a short readable pathway object."

            question_render_col.append(question_render)
            supporting_path_col.append("")
            direct_relation_col.append(direct_relation)
            proposed_path_col.append(proposed_path)
            construction_note_col.append(construction_note)
            continue

        supporting_path = _best_existing_support_path(row_s, label_map)
        bridge_label = _label_for(getattr(row, "focal_mediator_label", ""), label_map)
        if bridge_label:
            question_render = f"Could {source_label} affect {target_label} through {bridge_label}?"
        else:
            question_render = f"Could {source_label} affect {target_label}?"
        construction_note = (
            "The record proposes a missing direct relation. The support path is local graph evidence rather than proof."
            if supporting_path else
            "The record proposes a missing direct relation from the local graph."
        )
        question_render_col.append(question_render)
        supporting_path_col.append(supporting_path)
        direct_relation_col.append(direct_relation)
        proposed_path_col.append("")
        construction_note_col.append(construction_note)

    out["llm_question_render"] = question_render_col
    out["llm_supporting_path"] = supporting_path_col
    out["llm_existing_direct_relation"] = direct_relation_col
    out["llm_proposed_path"] = proposed_path_col
    out["llm_construction_note"] = construction_note_col
    return out


def _render_question_object(row: pd.Series, args: argparse.Namespace) -> tuple[str, dict[str, str]]:
    family_mode = _family_mode_for_row(row, args)
    source = _clean_text(row.get("source_label", ""))
    bridge = _clean_text(row.get("focal_mediator_label", ""))
    target = _clean_text(row.get("target_label", ""))
    direct_relation = _relation_text(source, target)
    path_relation = _clean_text(row.get("llm_supporting_path", "")) or (_path_text(source, bridge, target) if bridge else "")
    question_render_override = _clean_text(row.get("llm_question_render", ""))
    construction_note_override = _clean_text(row.get("llm_construction_note", ""))

    if family_mode == "direct_to_path":
        question_render = question_render_override or (
            f"Could {source} affect {target} through {bridge}?"
            if source and target and bridge
            else f"What channel could link {source} to {target}?"
        )
        construction_note = construction_note_override or (
            "The record starts from an existing direct relation and proposes a missing channel or bridge around it."
        )
        record = {
            "family": family_mode,
            "question_render": question_render,
            "existing_direct_relation": _clean_text(row.get("llm_existing_direct_relation", "")) or direct_relation,
            "proposed_path": _clean_text(row.get("llm_proposed_path", "")) or path_relation,
            "source_label": source,
            "bridge_label": bridge,
            "target_label": target,
            "construction_note": construction_note,
        }
        return question_render, record

    question_render = question_render_override or (
        f"Could {source} affect {target}?"
        if source and target
        else _relation_text(source, target)
    )
    construction_note = construction_note_override or (
        "The record proposes a missing direct relation. If a support path is shown, it is local graph support rather than proof."
    )
    record = {
        "family": family_mode,
        "question_render": question_render,
        "proposed_direct_relation": _clean_text(row.get("llm_existing_direct_relation", "")) or direct_relation,
        "supporting_path": path_relation,
        "source_label": source,
        "bridge_label": bridge,
        "target_label": target,
        "construction_note": construction_note,
    }
    return question_render, record


def _request_body(row: pd.Series, args: argparse.Namespace) -> dict[str, Any]:
    _, record = _render_question_object(row, args)
    record = {"item_id": row["item_id"], **record}
    user_prompt = USER_TEMPLATE.format(record_json=json.dumps(record, ensure_ascii=True, sort_keys=True))
    return {
        "model": args.model,
        "reasoning": {"effort": args.reasoning_effort},
        "max_output_tokens": int(args.max_output_tokens),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "historical_appendix_usefulness_v1",
                "strict": True,
                "schema": SCHEMA,
            },
        },
    }


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"

    bootstrap_manifest = {
        "status": "starting",
        "panel_path": str(args.panel_path),
        "corpus_path": str(args.corpus_path),
        "adopted_configs_path": str(args.adopted_configs_path),
        "family_mode": str(args.family_mode),
        "arms": [x.strip() for x in str(args.arms).split(",") if x.strip()],
        "top_k": int(args.top_k),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "max_output_tokens": int(args.max_output_tokens),
    }
    manifest_path.write_text(json.dumps(bootstrap_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[hist-usefulness] out_dir={out_dir}", flush=True)
    print(f"[hist-usefulness] panel={args.panel_path}", flush=True)

    panel_df = pd.read_parquet(args.panel_path)
    manifest = json.loads(Path(args.manifest_path).read_text(encoding="utf-8"))
    corpus_df = load_corpus(args.corpus_path)
    adopted = _load_adopted_configs(Path(args.adopted_configs_path))
    arms = [x.strip() for x in str(args.arms).split(",") if x.strip()]
    print(
        f"[hist-usefulness] panel_rows={len(panel_df):,} corpus_rows={len(corpus_df):,} "
        f"arms={arms}"
    , flush=True)

    report_years = [int(x) for x in manifest["report_cutoff_years"]]
    use_horizons = [int(x) for x in manifest["horizons"]]
    max_year = int(corpus_df["year"].max())
    pool_flag = f"in_pool_{int(manifest['pool_size'])}"
    panel_df = panel_df[panel_df[pool_flag].astype(int) == 1].copy()
    print(
        f"[hist-usefulness] report_years={report_years} horizons={use_horizons} "
        f"pool_flag={pool_flag} pooled_rows={len(panel_df):,}"
    , flush=True)

    selected_rows: list[pd.DataFrame] = []
    for horizon in use_horizons:
        block = panel_df[
            (panel_df["horizon"].astype(int) == int(horizon))
            & ((panel_df["cutoff_year_t"].astype(int) + int(horizon)) <= max_year)
        ].copy()
        if block.empty:
            continue
        spec = adopted[int(horizon)]
        print(
            f"[hist-usefulness] horizon={int(horizon)} block_rows={len(block):,} "
            f"adopted={spec['model_kind']}|{spec['feature_family']}|alpha={float(spec['alpha']):.2f}"
        , flush=True)
        for cutoff_t in report_years:
            eval_rows = block[block["cutoff_year_t"].astype(int) == int(cutoff_t)].copy()
            train_rows = block[block["cutoff_year_t"].astype(int) < int(cutoff_t)].copy()
            if eval_rows.empty:
                continue

            rankings: dict[str, pd.DataFrame] = {}
            if "transparent" in arms:
                transparent = (
                    eval_rows[["u", "v", "transparent_score"]]
                    .rename(columns={"transparent_score": "score"})
                    .sort_values(["score", "u", "v"], ascending=[False, True, True])
                    .reset_index(drop=True)
                )
                transparent["rank"] = transparent.index + 1
                rankings["transparent"] = transparent

            if "pref_attach" in arms:
                train_corpus = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
                pref = pref_attach_ranking_from_universe(
                    train_corpus,
                    candidate_pairs_df=eval_rows[[c for c in ["u", "v", "candidate_kind"] if c in eval_rows.columns]].copy(),
                )
                rankings["pref_attach"] = pref

            if "adopted" in arms and not train_rows.empty and train_rows["appears_within_h"].nunique() >= 2:
                model = _fit_model(
                    train_rows=train_rows,
                    model_kind=str(spec["model_kind"]),
                    feature_family=str(spec["feature_family"]),
                    alpha=float(spec["alpha"]),
                    seed=int(args.seed) + int(cutoff_t) + int(horizon),
                )
                if model is not None:
                    rankings["adopted"] = score_with_reranker(eval_rows, model)

            for arm_name, ranked_df in rankings.items():
                top = ranked_df.head(int(args.top_k)).copy()
                merged = top.merge(eval_rows, on=["u", "v"], how="left", suffixes=("", "_panel"))
                merged["selection_arm"] = str(arm_name)
                merged["selection_horizon"] = int(horizon)
                merged["cutoff_year_t"] = int(cutoff_t)
                merged["selection_rank"] = pd.to_numeric(merged["rank"], errors="coerce").fillna(0).astype(int)
                selected_rows.append(merged)
            if rankings:
                print(
                    f"[hist-usefulness] horizon={int(horizon)} cutoff={int(cutoff_t)} "
                    f"eval_rows={len(eval_rows):,} train_rows={len(train_rows):,} "
                    f"arms_built={sorted(rankings.keys())}"
                , flush=True)

    selected_df = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
    if selected_df.empty:
        bootstrap_manifest["status"] = "failed_empty_selection"
        manifest_path.write_text(json.dumps(bootstrap_manifest, indent=2) + "\n", encoding="utf-8")
        raise ValueError("No selected rows were generated")

    selected_df = selected_df.sort_values(
        ["selection_horizon", "cutoff_year_t", "selection_arm", "selection_rank", "u", "v"],
        kind="mergesort",
    ).reset_index(drop=True)
    selected_df["item_id"] = [
        f"hist_uv1_h{int(row.selection_horizon)}_t{int(row.cutoff_year_t)}_{str(row.selection_arm)}_{int(row.selection_rank):03d}"
        for row in selected_df.itertuples(index=False)
    ]
    print(f"[hist-usefulness] selected_rows={len(selected_df):,}; augmenting question objects", flush=True)
    selected_df = _augment_question_objects(selected_df, corpus_df=corpus_df, args=args)
    print("[hist-usefulness] question-object augmentation complete", flush=True)

    requests_path = out_dir / "historical_usefulness_requests.jsonl"
    selected_csv = out_dir / "historical_usefulness_selected_items.csv"
    system_md = out_dir / "system_prompt.md"
    user_md = out_dir / "user_prompt_template.md"
    schema_json = out_dir / "schema_historical_appendix_usefulness_v1.json"

    with requests_path.open("w", encoding="utf-8") as fh:
        for row in selected_df.to_dict(orient="records"):
            payload = {
                "custom_id": row["item_id"],
                "method": "POST",
                "url": "/v1/responses",
                "body": _request_body(pd.Series(row), args),
            }
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    selected_df.to_csv(selected_csv, index=False)
    system_md.write_text(SYSTEM_PROMPT + "\n", encoding="utf-8")
    user_md.write_text(USER_TEMPLATE + "\n", encoding="utf-8")
    schema_json.write_text(json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")

    requests_n = int(len(selected_df))
    manifest_out = {
        "status": "completed",
        "panel_path": str(args.panel_path),
        "corpus_path": str(args.corpus_path),
        "adopted_configs_path": str(args.adopted_configs_path),
        "family_mode": str(args.family_mode),
        "report_cutoff_years": report_years,
        "horizons": use_horizons,
        "arms": arms,
        "top_k": int(args.top_k),
        "n_requests": requests_n,
        "selected_csv": str(selected_csv),
        "request_jsonl": str(requests_path),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "max_output_tokens": int(args.max_output_tokens),
    }
    manifest_path.write_text(json.dumps(manifest_out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest_out, indent=2), flush=True)


if __name__ == "__main__":
    main()
