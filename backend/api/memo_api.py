"""Credit Memo API blueprint.

Every route is mounted under /api by WEBAIKU.extend() (keep routes relative).
Reads/writes the DSS datasets and managed folders, runs the agent, and renders
matplotlib snippets. Returns JSON.

Multi-memo: every row is scoped by memo_id (= the memo title).
  - structure_memo : memo_id, title, description, metrics   (the structure)
  - credit_memo    : memo_id, title, content                (agent output)
  - metrics        : metric, description                    (selectable catalog)
"""
import traceback

import dataiku
import pandas as pd
from flask import Blueprint, jsonify, request

from ..config import (
    AGENT_NAME,
    DATASET_NAME,
    MEMO_COLS,
    MEMO_DATASET,
    METRICS_DATASET,
    METRICS_FOLDER,
    PDF_FOLDER,
    STRUCT_COLS,
)

memo_api = Blueprint("memo_api", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_df(name):
    try:
        df = dataiku.Dataset(name).get_dataframe()
    except Exception:  # noqa: BLE001
        return None
    if df is None or df.empty:
        return None
    return df


def ensure_cols(df, cols):
    for col in cols:
        if col not in df.columns:
            df[col] = ""
    return df


def memo_mask(df, memo_id):
    return df["memo_id"].fillna("").astype(str).str.strip().str.lower() == memo_id.strip().lower()


def find_agent(project):
    for agent in project.list_agents():
        if agent.name == AGENT_NAME or agent.id == AGENT_NAME:
            return project.get_agent(agent.id)
    raise ValueError("Agent not found: %s" % AGENT_NAME)


def list_memos():
    ids = set()
    for name in (DATASET_NAME, MEMO_DATASET):
        df = read_df(name)
        if df is not None and "memo_id" in df.columns:
            for value in df["memo_id"].dropna().astype(str):
                if value.strip():
                    ids.add(value.strip())
    return sorted(ids, key=lambda s: s.lower())


def read_metrics_catalog():
    df = read_df(METRICS_DATASET)
    items, seen = [], set()
    if df is not None and "metric" in df.columns:
        for _, row in df.iterrows():
            name = ("" if pd.isna(row.get("metric")) else str(row.get("metric"))).strip()
            desc = ("" if pd.isna(row.get("description")) else str(row.get("description"))).strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                items.append({"metric": name, "description": desc})
    return items


def read_generated(memo_id=None):
    df = read_df(MEMO_DATASET)
    if df is None:
        return []
    df = ensure_cols(df, MEMO_COLS)
    if memo_id and "memo_id" in df.columns:
        df = df[memo_mask(df, memo_id)]
    return df[["title", "content"]].fillna("").to_dict(orient="records")


def structure_rows(payload):
    memo_id = (payload.get("memo_title") or "").strip()
    rows = [
        {
            "memo_id": memo_id,
            "title": (b.get("title") or "").strip(),
            "description": (b.get("description") or "").strip(),
            "metrics": (b.get("metrics") or "").strip(),
        }
        for b in payload.get("blocks", [])
    ]
    return memo_id, pd.DataFrame(rows, columns=STRUCT_COLS)


def upsert_structure(payload):
    memo_id, new_rows = structure_rows(payload)
    existing = read_df(DATASET_NAME)
    if existing is not None and "memo_id" in existing.columns:
        existing = ensure_cols(existing, STRUCT_COLS)
        others = existing[~memo_mask(existing, memo_id)][STRUCT_COLS]
        combined = pd.concat([others, new_rows], ignore_index=True)
    else:
        combined = new_rows
    dataiku.Dataset(DATASET_NAME).write_with_schema(combined)


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------
@memo_api.route("/metrics")
def get_metrics():
    return jsonify({"items": read_metrics_catalog()})


@memo_api.route("/memos")
def get_memos():
    return jsonify({"memos": list_memos()})


@memo_api.route("/memo")
def get_memo():
    memo_id = (request.args.get("memo_id") or "").strip()
    blocks = []
    df = read_df(DATASET_NAME)
    if df is not None:
        df = ensure_cols(df, STRUCT_COLS)
        if memo_id and "memo_id" in df.columns:
            df = df[memo_mask(df, memo_id)]
        blocks = df[["title", "description", "metrics"]].fillna("").to_dict(orient="records")
    return jsonify({"memo_title": memo_id, "blocks": blocks, "generated": read_generated(memo_id)})


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------
@memo_api.route("/structure", methods=["POST"])
def save_structure():
    try:
        payload = request.get_json(force=True) or {}
        upsert_structure(payload)
        return jsonify({"status": "ok", "count": len(payload.get("blocks", [])), "memos": list_memos()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/run_agent", methods=["POST"])
def run_agent():
    try:
        payload = request.get_json(force=True) or {}
        upsert_structure(payload)
        memo_id = (payload.get("memo_title") or "").strip()
        project = dataiku.api_client().get_default_project()
        agent = find_agent(project)
        agent.as_llm().new_completion().with_message(memo_id).execute()
        return jsonify({"status": "ok", "items": read_generated(memo_id), "memos": list_memos()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/clear_generated", methods=["POST"])
def clear_generated():
    try:
        memo_id = ((request.get_json(force=True) or {}).get("memo_title") or "").strip()
        df = read_df(MEMO_DATASET)
        if df is not None and "memo_id" in df.columns:
            dataiku.Dataset(MEMO_DATASET).write_with_schema(df[~memo_mask(df, memo_id)])
        return jsonify({"status": "ok"})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/delete_generated", methods=["POST"])
def delete_generated():
    try:
        payload = request.get_json(force=True) or {}
        memo_id = (payload.get("memo_title") or "").strip()
        target = (payload.get("title") or "").strip().lower()
        df = read_df(MEMO_DATASET)
        if df is not None and "memo_id" in df.columns and "title" in df.columns:
            same = df["title"].fillna("").str.strip().str.lower() == target
            dataiku.Dataset(MEMO_DATASET).write_with_schema(df[~(memo_mask(df, memo_id) & same)])
        return jsonify({"status": "ok", "items": read_generated(memo_id)})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/delete_memo", methods=["POST"])
def delete_memo():
    try:
        memo_id = ((request.get_json(force=True) or {}).get("memo_title") or "").strip()
        for name in (DATASET_NAME, MEMO_DATASET):
            df = read_df(name)
            if df is not None and "memo_id" in df.columns:
                dataiku.Dataset(name).write_with_schema(df[~memo_mask(df, memo_id)])
        return jsonify({"status": "ok", "memos": list_memos()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/import_memo", methods=["POST"])
def import_memo():
    """Empty the "Previous Memos PDF" folder, drop the uploaded document into it,
    then rebuild structure_memo (runs the extraction chain)."""
    try:
        f = request.files.get("file")
        if f is None:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400
        before_ids = set(m.lower() for m in list_memos())

        pdf_folder = dataiku.Folder(PDF_FOLDER)
        for path in pdf_folder.list_paths_in_partition():
            pdf_folder.delete_path(path)
        pdf_folder.upload_stream(f.filename, f.read())

        dataiku.api_client().get_default_project().start_job_and_wait({
            "type": "RECURSIVE_FORCED_BUILD",
            "outputs": [{"type": "DATASET", "id": DATASET_NAME}],
        })

        memos = list_memos()
        new_ids = [m for m in memos if m.lower() not in before_ids]
        return jsonify({"status": "ok", "memos": memos, "new_ids": new_ids})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/add_metrics", methods=["POST"])
def add_metrics():
    """Drop metric documents into the folder, then run BUILD_METRICS."""
    try:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400
        folder = dataiku.Folder(METRICS_FOLDER)
        for f in files:
            folder.upload_stream(f.filename, f.read())
        dataiku.api_client().get_default_project().get_scenario("BUILD_METRICS").run_and_wait()
        return jsonify({"status": "ok", "items": read_metrics_catalog()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/run_python", methods=["POST"])
def run_python():
    """Execute a matplotlib snippet (from a <python> block) -> base64 PNG.
    Runs agent-provided code server-side; trusted self-hosted project only."""
    try:
        import base64
        import io as _io

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        code = ((request.get_json(force=True) or {}).get("code") or "")
        plt.close("all")
        exec(code, {"__name__": "__agent_chart__"})  # noqa: S102
        nums = plt.get_fignums()
        if not nums:
            return jsonify({"status": "error", "message": "No figure was produced."})
        plt.figure(nums[-1])
        buf = _io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        plt.close("all")
        return jsonify({"status": "ok", "image": base64.b64encode(buf.getvalue()).decode("ascii")})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)})
