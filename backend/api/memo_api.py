"""Credit Memo API blueprint.

Every route is mounted under /api by WEBAIKU.extend() (keep routes relative).
Reads/writes the DSS datasets and managed folders, runs the agent, and renders
matplotlib snippets. Returns JSON.

Multi-memo: every row is scoped by memo_id (= the memo title).
  - structure_memo : memo_id, title, description, metrics   (the structure)
  - credit_memo    : memo_id, title, content                (agent output)
  - metrics        : metric, description                    (selectable catalog)
"""
import json
import re
import traceback

import dataiku
import pandas as pd
from flask import Blueprint, Response, jsonify, request

from ..config import (
    AGENT_NAME,
    KPI_EXTRACTION_AGENT,
    ALL_KPI_DATASET,
    DATA_FOLDER,
    DATASET_NAME,
    INPUT_KPI_DATASET,
    KPI_FORMULA_GROUP,
    KPI_RECIPE,
    MEMO_COLS,
    MEMO_DATASET,
    METRIC_COL_SUFFIX,
    METRICS_DATASET,
    METRICS_FOLDER,
    OUTPUT_KPI_DATASET,
    PDF_FOLDER,
    SCENARIO_BUILD_METRICS,
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


def find_named_agent(project, name_or_id):
    for agent in project.list_agents():
        if agent.name == name_or_id or agent.id == name_or_id:
            return project.get_agent(agent.id)
    raise ValueError("Agent not found: %s" % name_or_id)


def find_agent(project):
    return find_named_agent(project, AGENT_NAME)


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


@memo_api.route("/generated")
def get_generated_route():
    """Paragraphs currently in credit_memo for a memo (used to poll during a run)."""
    memo_id = (request.args.get("memo_id") or "").strip()
    return jsonify({"items": read_generated(memo_id)})


@memo_api.route("/all_kpi")
def get_all_kpi():
    """Catalog of KPIs selectable in the Builder, from the all_KPI dataset."""
    df = read_df(ALL_KPI_DATASET)
    items, seen = [], set()
    if df is not None:
        name_col = next((c for c in ("kpi", "KPI", "name", "metric") if c in df.columns),
                        df.columns[0] if len(df.columns) else None)
        cat_col = "category" if "category" in df.columns else None
        if name_col is not None:
            for _, row in df.iterrows():
                nm = ("" if pd.isna(row.get(name_col)) else str(row.get(name_col))).strip()
                if nm and nm.lower() not in seen:
                    seen.add(nm.lower())
                    cat = ("" if not cat_col or pd.isna(row.get(cat_col)) else str(row.get(cat_col))).strip()
                    items.append({"kpi": nm, "category": cat})
    return jsonify({"items": items})


@memo_api.route("/input_kpi")
def get_input_kpi():
    """The KPIs the agent extracted into input_KPI, as {columns, rows}."""
    df = read_df(INPUT_KPI_DATASET)
    if df is None:
        return jsonify({"columns": [], "rows": []})
    safe = df.astype(object).where(pd.notna(df), None)
    return jsonify({"columns": [str(c) for c in safe.columns], "rows": safe.values.tolist()})


def _strip_sheet_suffix(name):
    """"TerraNova_...DebtSchedule.xlsx (Debt Schedule)" -> the file name only.

    The pipeline may append the source sheet name in parentheses to Excel
    document names; strip it so the file resolves in the folder."""
    return re.sub(r"\s*\([^()]*\)\s*$", "", name or "").strip()


def _find_in_data_folder(name):
    """Resolve a file (by full path or basename) inside the Data folder,
    tolerating a trailing " (Sheet Name)" suffix on Excel documents."""
    folder = dataiku.Folder(DATA_FOLDER)
    candidates = [name]
    stripped = _strip_sheet_suffix(name)
    if stripped and stripped != name:
        candidates.append(stripped)
    wanted = set()
    for c in candidates:
        c = (c or "").lstrip("/")
        wanted.add(c)
        wanted.add(c.split("/")[-1])
    for p in folder.list_paths_in_partition():
        clean = p.lstrip("/")
        if clean in wanted or clean.split("/")[-1] in wanted:
            return folder, p
    return folder, None


@memo_api.route("/document")
def get_document():
    """Stream a source document (by file name) from the Data managed folder."""
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"error": "missing name"}), 400
    folder, target = _find_in_data_folder(name)
    if target is None:
        return jsonify({"error": "not found: %s" % name}), 404
    with folder.get_download_stream(target) as stream:
        data = stream.read()
    mimetype = "application/pdf" if target.lower().endswith(".pdf") else "application/octet-stream"
    return Response(data, mimetype=mimetype)


def _excel_cell(v):
    """Human-friendly string for an Excel cell value."""
    if v is None:
        return ""
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else ("%.4f" % v).rstrip("0").rstrip(".")
    try:
        import datetime
        if isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)):
            return str(v)[:10]
    except Exception:  # noqa: BLE001
        pass
    return str(v)


@memo_api.route("/excel_preview")
def excel_preview():
    """Preview an Excel source: every sheet as {name, columns, rows} (truncated)."""
    import io as _io

    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"error": "missing name"}), 400
    folder, target = _find_in_data_folder(name)
    if target is None:
        return jsonify({"error": "not found: %s" % name}), 404
    with folder.get_download_stream(target) as stream:
        data = stream.read()
    try:
        sheets_dict = pd.read_excel(_io.BytesIO(data), sheet_name=None, header=0)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"error": "Could not read Excel file: %s" % exc}), 500

    max_rows = 200
    sheets = []
    for sname, full in sheets_dict.items():
        total = int(len(full))
        view = full.head(max_rows)
        safe = view.astype(object).where(pd.notna(view), None)
        cols = ["" if re.match(r"^Unnamed: \d+$", str(c)) else str(c) for c in safe.columns]
        rows = [[_excel_cell(v) for v in rec] for rec in safe.values.tolist()]
        sheets.append({
            "name": str(sname),
            "columns": cols,
            "rows": rows,
            "truncated": total > max_rows,
            "total_rows": total,
        })
    return jsonify({"sheets": sheets})


# ---------------------------------------------------------------------------
# KPI lineage (formula -> metrics -> source documents)
# ---------------------------------------------------------------------------
def _norm_key(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _load_recipe_payload():
    """Return the prepare recipe steps payload as a dict (or None)."""
    recipe = dataiku.api_client().get_default_project().get_recipe(KPI_RECIPE)
    raw = recipe.get_definition_and_payload().get_payload()
    return json.loads(raw) if raw else None


def _walk_formula_steps(steps, in_group, group_name):
    """(column, expression) for formula steps, restricted to the target group
    when present (recurses into nested groups)."""
    out = []
    for step in steps or []:
        stype = step.get("type", "")
        name = step.get("name") or (step.get("params") or {}).get("name") or ""
        if step.get("metaType") == "GROUP" or "steps" in step:
            deeper = in_group or (_norm_key(name) == _norm_key(group_name))
            out += _walk_formula_steps(step.get("steps", []), deeper, group_name)
        elif stype == "CreateColumnWithGREL" or "GREL" in stype or "Formula" in stype:
            if in_group:
                p = step.get("params", {})
                col, expr = p.get("column"), p.get("expression")
                if col and expr:
                    out.append((col, expr))
    return out


def _extract_formulas(payload):
    """{normalized_column: {column, formula}} from the KPI formula group."""
    steps = payload.get("steps", [])
    pairs = _walk_formula_steps(steps, False, KPI_FORMULA_GROUP)
    if not pairs:  # named group not found → take every formula step
        pairs = _walk_formula_steps(steps, True, KPI_FORMULA_GROUP)
    return {_norm_key(col): {"column": col, "formula": expr} for col, expr in pairs}


def _renamings(steps):
    """All (from, to) column renamings across the recipe, in order."""
    out = []
    for step in steps or []:
        if step.get("metaType") == "GROUP" or "steps" in step:
            out += _renamings(step.get("steps", []))
        elif "Rename" in step.get("type", ""):
            for r in (step.get("params", {}) or {}).get("renamings", []) or []:
                if r.get("from") and r.get("to"):
                    out.append((r["from"], r["to"]))
    return out


def _value_columns(payload):
    """{current_column_name: base_metric} for wide metric-value columns,
    following the recipe's renames (e.g. capex -> Capital expenditure)."""
    renamings = _renamings(payload.get("steps", []))
    origin = {}  # current name -> earliest original name
    for frm, to in renamings:
        origin[to] = origin.get(frm, frm)
    result = {}
    for _frm, to in renamings:
        org = origin.get(to, to)
        if org.endswith(METRIC_COL_SUFFIX):
            result[to] = org[: -len(METRIC_COL_SUFFIX)]
    return result


def _metrics_in_formula(expr, value_cols):
    """Base metric names referenced in a formula, resolving renamed columns."""
    found = set()
    # renamed columns (e.g. `capex`) referenced by their current name
    for name, base in value_cols.items():
        if re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])', expr):
            found.add(base)
    # plus any original *_metric_value_first columns referenced directly
    suffix = re.escape(METRIC_COL_SUFFIX)
    for n in re.findall(r'"([^"]*?' + suffix + r')"', expr):
        found.add(n[: -len(METRIC_COL_SUFFIX)])
    for n in re.findall(r'\b([A-Za-z0-9_]+' + suffix + r')\b', expr):
        found.add(n[: -len(METRIC_COL_SUFFIX)])
    return sorted(found)


def _sources_by_metric():
    """{normalized_metric: {metric, sources:[{source, quote}]}} from input_KPI."""
    df = read_df(INPUT_KPI_DATASET)
    if df is None:
        return {}
    for col in ("metric", "source", "quote"):
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    acc = {}
    for _, row in df.iterrows():
        metric = str(row["metric"]).strip()
        if not metric:
            continue
        bucket = acc.setdefault(_norm_key(metric), {"metric": metric, "sources": {}})
        src = str(row["source"]).strip()
        if src and src not in bucket["sources"]:
            bucket["sources"][src] = str(row["quote"])
    return {
        k: {"metric": v["metric"], "sources": [{"source": s, "quote": q} for s, q in v["sources"].items()]}
        for k, v in acc.items()
    }


@memo_api.route("/kpi_lineage")
def get_kpi_lineage():
    """Per KPI in output_KPI: formula, metrics used, and their source documents."""
    formulas, value_cols = {}, {}
    try:
        payload = _load_recipe_payload()
        if payload:
            formulas = _extract_formulas(payload)
            value_cols = _value_columns(payload)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    sources = _sources_by_metric()

    out_df = read_df(OUTPUT_KPI_DATASET)
    kpis, seen = [], {}
    if out_df is not None:
        for col in ("kpi", "category", "fiscal_year", "kpi_value"):
            if col not in out_df.columns:
                out_df[col] = None
        out_df = out_df.astype(object).where(pd.notna(out_df), None)
        for _, row in out_df.iterrows():
            name = str(row["kpi"] or "").strip()
            if not name:
                continue
            if name not in seen:
                fk = _norm_key(name)
                f = formulas.get(fk)
                if f is None:
                    for k, v in formulas.items():
                        if fk and (fk in k or k in fk):
                            f = v
                            break
                formula = f["formula"] if f else ""
                metrics = [
                    {"metric": mn, "sources": (sources.get(_norm_key(mn)) or {}).get("sources", [])}
                    for mn in (_metrics_in_formula(formula, value_cols) if formula else [])
                ]
                seen[name] = {
                    "kpi": name,
                    "category": str(row["category"] or ""),
                    "formula": formula,
                    "metrics": metrics,
                    "values": [],
                }
                kpis.append(seen[name])
            seen[name]["values"].append({"fiscal_year": row["fiscal_year"], "kpi_value": row["kpi_value"]})
    return jsonify({"kpis": kpis, "formulas_found": len(formulas)})


@memo_api.route("/kpi_full")
def get_kpi_full():
    """Merged KPI catalog from all_KPI.

    - KPIs computed by the prepare recipe (present in output_KPI) get the full
      lineage: formula, metrics used, and their source documents.
    - Input metrics only carry their source documents (from input_KPI).
    """
    formulas, value_cols = {}, {}
    try:
        payload = _load_recipe_payload()
        if payload:
            formulas = _extract_formulas(payload)
            value_cols = _value_columns(payload)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    sources = _sources_by_metric()

    def find_formula(name):
        fk = _norm_key(name)
        f = formulas.get(fk)
        if f is None:
            for k, v in formulas.items():
                if fk and (fk in k or k in fk):
                    return v
        return f

    # Values per computed KPI, from output_KPI.
    computed_values = {}
    out_df = read_df(OUTPUT_KPI_DATASET)
    if out_df is not None:
        out_df = ensure_cols(out_df, ["kpi", "fiscal_year", "kpi_value"])
        d = out_df.astype(object).where(pd.notna(out_df), None)
        for _, row in d.iterrows():
            nm = str(row["kpi"] or "").strip()
            if nm:
                bucket = computed_values.setdefault(_norm_key(nm), {"name": nm, "values": []})
                bucket["values"].append({"fiscal_year": row["fiscal_year"], "kpi_value": row["kpi_value"]})

    # Values per input metric, from input_KPI.
    input_values = {}
    in_df = read_df(INPUT_KPI_DATASET)
    if in_df is not None:
        in_df = ensure_cols(in_df, ["metric", "fiscal_year", "metric_value"])
        d = in_df.astype(object).where(pd.notna(in_df), None)
        for _, row in d.iterrows():
            nm = str(row["metric"] or "").strip()
            if nm:
                input_values.setdefault(_norm_key(nm), []).append(
                    {"fiscal_year": row["fiscal_year"], "kpi_value": row["metric_value"]})

    # Catalog from all_KPI (falls back to the union of the two datasets).
    entries, seen = [], {}
    df = read_df(ALL_KPI_DATASET)
    if df is not None:
        name_col = next((c for c in ("kpi", "KPI", "name", "metric") if c in df.columns),
                        df.columns[0] if len(df.columns) else None)
        cat_col = "category" if "category" in df.columns else None
        year_col = next((c for c in ("fiscal_year", "year") if c in df.columns), None)
        val_col = next((c for c in ("kpi_value", "value", "metric_value") if c in df.columns), None)
        d = df.astype(object).where(pd.notna(df), None)
        for _, row in d.iterrows():
            nm = str(row[name_col] or "").strip() if name_col else ""
            if not nm:
                continue
            k = _norm_key(nm)
            if k not in seen:
                seen[k] = {"kpi": nm,
                           "category": str(row[cat_col] or "").strip() if cat_col else "",
                           "values": []}
                entries.append(seen[k])
            if year_col and val_col and row[val_col] is not None:
                seen[k]["values"].append({"fiscal_year": row[year_col], "kpi_value": row[val_col]})
    else:
        for k, v in computed_values.items():
            seen[k] = {"kpi": v["name"], "category": "", "values": []}
            entries.append(seen[k])
        for k in input_values:
            if k not in seen:
                nm = (sources.get(k) or {}).get("metric") or k
                seen[k] = {"kpi": nm, "category": "", "values": []}
                entries.append(seen[k])

    items = []
    for e in entries:
        k = _norm_key(e["kpi"])
        comp = computed_values.get(k)
        if comp is None:
            for ck, cv in computed_values.items():
                if k and (k in ck or ck in k):
                    comp = cv
                    break
        if comp is not None:
            f = find_formula(e["kpi"])
            formula = f["formula"] if f else ""
            metrics = [
                {"metric": mn, "sources": (sources.get(_norm_key(mn)) or {}).get("sources", [])}
                for mn in (_metrics_in_formula(formula, value_cols) if formula else [])
            ]
            items.append({"kpi": e["kpi"], "category": e["category"], "type": "computed",
                          "formula": formula, "metrics": metrics,
                          "values": e["values"] or comp["values"]})
        else:
            items.append({"kpi": e["kpi"], "category": e["category"], "type": "input",
                          "sources": (sources.get(k) or {}).get("sources", []),
                          "values": e["values"] or input_values.get(k, [])})
    return jsonify({"items": items})


@memo_api.route("/recipe_debug")
def recipe_debug():
    """Dump the KPI recipe payload (calibration aid for the formula parser)."""
    try:
        return jsonify({"payload": _load_recipe_payload()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


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


@memo_api.route("/run_agent_section", methods=["POST"])
def run_agent_section():
    """Regenerate a SINGLE section, optionally following a revision instruction.

    The DSS agent is driven by a memo_id (it reads structure_memo for that id and
    writes paragraphs to credit_memo). To touch only one section we spin up a
    throwaway memo_id holding just this block — with the current draft and the
    user's instruction folded into its brief — run the agent on it, copy the
    resulting paragraph back onto the real memo, then delete the temp rows.
    """
    try:
        import uuid

        payload = request.get_json(force=True) or {}
        memo_id = (payload.get("memo_title") or "").strip()
        block = payload.get("block") or {}
        title = (block.get("title") or "").strip()
        if not memo_id or not title:
            return jsonify({"status": "error", "message": "memo_title and block.title are required"}), 400

        description = (block.get("description") or "").strip()
        metrics = (block.get("metrics") or "").strip()
        instruction = (payload.get("instruction") or "").strip()
        previous = (payload.get("previous") or "").strip()

        # Brief for the one-section run: original brief + current draft + edit ask.
        brief = description
        if previous:
            brief += "\n\n--- CURRENT DRAFT ---\n" + previous
        if instruction:
            brief += "\n\n--- REVISION INSTRUCTION ---\n" + instruction
        brief += "\n\n(Rewrite only this section accordingly.)"

        temp_id = "__section__" + uuid.uuid4().hex

        # 1) Append a single throwaway structure row.
        struct = read_df(DATASET_NAME)
        temp_row = pd.DataFrame(
            [{"memo_id": temp_id, "title": title, "description": brief, "metrics": metrics}],
            columns=STRUCT_COLS,
        )
        if struct is not None and "memo_id" in struct.columns:
            struct = ensure_cols(struct, STRUCT_COLS)
            combined = pd.concat([struct[STRUCT_COLS], temp_row], ignore_index=True)
        else:
            combined = temp_row
        dataiku.Dataset(DATASET_NAME).write_with_schema(combined)

        try:
            # 2) Run the agent on just that temp memo.
            project = dataiku.api_client().get_default_project()
            agent = find_agent(project)
            agent.as_llm().new_completion().with_message(temp_id).execute()

            # 3) Read the paragraph the agent produced for the temp memo.
            mem = read_df(MEMO_DATASET)
            new_content = ""
            if mem is not None:
                mem = ensure_cols(mem, MEMO_COLS)
                same_title = mem["title"].fillna("").astype(str).str.strip().str.lower() == title.lower()
                hits = mem[memo_mask(mem, temp_id) & same_title]
                if not hits.empty:
                    new_content = str(hits.iloc[-1]["content"] or "")
        finally:
            # 4) Always clean up temp rows (structure + credit_memo).
            struct2 = read_df(DATASET_NAME)
            if struct2 is not None and "memo_id" in struct2.columns:
                struct2 = ensure_cols(struct2, STRUCT_COLS)
                dataiku.Dataset(DATASET_NAME).write_with_schema(struct2[~memo_mask(struct2, temp_id)][STRUCT_COLS])
            memc = read_df(MEMO_DATASET)
            if memc is not None and "memo_id" in memc.columns:
                memc = ensure_cols(memc, MEMO_COLS)
                dataiku.Dataset(MEMO_DATASET).write_with_schema(memc[~memo_mask(memc, temp_id)][MEMO_COLS])

        if not new_content.strip():
            return jsonify({"status": "error", "message": "Agent produced no output for this section.",
                            "items": read_generated(memo_id)}), 200

        # 5) Replace this section's paragraph on the real memo.
        mem3 = read_df(MEMO_DATASET)
        mem3 = ensure_cols(mem3, MEMO_COLS) if mem3 is not None else pd.DataFrame(columns=MEMO_COLS)
        same_title = mem3["title"].fillna("").astype(str).str.strip().str.lower() == title.lower()
        kept = mem3[~(memo_mask(mem3, memo_id) & same_title)][MEMO_COLS]
        new_row = pd.DataFrame([{"memo_id": memo_id, "title": title, "content": new_content}], columns=MEMO_COLS)
        dataiku.Dataset(MEMO_DATASET).write_with_schema(pd.concat([kept, new_row], ignore_index=True))

        return jsonify({"status": "ok", "items": read_generated(memo_id), "content": new_content})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/save_generated", methods=["POST"])
def save_generated():
    """Overwrite one section's paragraph with user-edited content (manual edit)."""
    try:
        payload = request.get_json(force=True) or {}
        memo_id = (payload.get("memo_title") or "").strip()
        title = (payload.get("title") or "").strip()
        content = payload.get("content") or ""
        if not memo_id or not title:
            return jsonify({"status": "error", "message": "memo_title and title are required"}), 400
        df = read_df(MEMO_DATASET)
        df = ensure_cols(df, MEMO_COLS) if df is not None else pd.DataFrame(columns=MEMO_COLS)
        same_title = df["title"].fillna("").astype(str).str.strip().str.lower() == title.lower()
        kept = df[~(memo_mask(df, memo_id) & same_title)][MEMO_COLS]
        new_row = pd.DataFrame([{"memo_id": memo_id, "title": title, "content": content}], columns=MEMO_COLS)
        dataiku.Dataset(MEMO_DATASET).write_with_schema(pd.concat([kept, new_row], ignore_index=True))
        return jsonify({"status": "ok", "items": read_generated(memo_id)})
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
        dataiku.api_client().get_default_project().get_scenario(SCENARIO_BUILD_METRICS).run_and_wait()
        return jsonify({"status": "ok", "items": read_metrics_catalog()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


def _input_kpi_state():
    df = read_df(INPUT_KPI_DATASET)
    if df is None:
        return {"columns": [], "rows": []}
    safe = df.astype(object).where(pd.notna(df), None)
    return {"columns": [str(c) for c in safe.columns], "rows": safe.values.tolist()}


@memo_api.route("/run_kpi_extraction", methods=["POST"])
def run_kpi_extraction():
    """Run the "KPI Extraction" agent, which fills the input_KPI dataset.

    Blocking call; the frontend polls /input_kpi meanwhile to show rows as the
    agent writes them."""
    try:
        project = dataiku.api_client().get_default_project()
        agent = find_named_agent(project, KPI_EXTRACTION_AGENT)
        agent.as_llm().new_completion().with_message(
            "Extract the KPIs from the source documents into the input_KPI dataset."
        ).execute()

        # Once the agent is done, build downstream (BUILD_METRICS scenario).
        try:
            project.get_scenario(SCENARIO_BUILD_METRICS).run_and_wait()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": "Agent finished, but scenario %s failed: %s" % (SCENARIO_BUILD_METRICS, exc),
                **_input_kpi_state(),
            }), 200

        return jsonify({"status": "ok", **_input_kpi_state()})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@memo_api.route("/clean_input_kpi", methods=["POST"])
def clean_input_kpi():
    """Dev tool: blank every column of input_KPI except metric & fiscal_year.

    Leaves the (metric, fiscal_year) skeleton so the KPI Filler agent can be
    re-run from a clean slate. Rows and schema are preserved."""
    try:
        keep = {"metric", "fiscal_year"}
        df = read_df(INPUT_KPI_DATASET)
        if df is None:
            return jsonify({"status": "ok", "columns": [], "rows": [], "cleared": []})
        cleared = [c for c in df.columns if c not in keep]
        for col in cleared:
            df[col] = None
        dataiku.Dataset(INPUT_KPI_DATASET).write_with_schema(df)
        safe = df.astype(object).where(pd.notna(df), None)
        return jsonify({
            "status": "ok",
            "columns": [str(c) for c in safe.columns],
            "rows": safe.values.tolist(),
            "cleared": cleared,
        })
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
