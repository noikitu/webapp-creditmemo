"""Project-specific configuration for the Credit Memo webapp.

These values differ between DSS projects (a copied project often renames
datasets while keeping managed-folder IDs) — verify against the target with
`dku dataset list` / `dku managed-folder list` before deploying.
"""

# Datasets
DATASET_NAME = "structure_memo"   # memo_id, title, description, metrics
MEMO_DATASET = "credit_memo"      # memo_id, title, content (agent output)
METRICS_DATASET = "metrics"       # metric, description (selectable catalog)
INPUT_KPI_DATASET = "input_KPI"   # metric, fiscal_year, metric_value, source, quote
OUTPUT_KPI_DATASET = "output_KPI" # fiscal_year, kpi, category, kpi_value

# KPI extraction
DATA_FOLDER = "IYNDI8sb"          # "Data" folder holding the source documents (PDF)

# KPI lineage: prepare recipe whose "Compute KPIs" group holds the formulas
KPI_RECIPE = "prep_compute_kpis_from_pdf_metrics"
KPI_FORMULA_GROUP = "Compute KPIs"   # step group holding the KPI formulas
METRIC_COL_SUFFIX = "_metric_value_first"  # wide-table column suffix for a metric

# Managed folders: {display_name: folder_id}
PDF_FOLDER = "8aTKpXsk"           # "Previous Memos PDF": cleared & filled on import
METRICS_FOLDER = "tiSmyWaP"       # "Documents Metrics": metric documents dropped here

# Agent
AGENT_NAME = "Credit Memo"        # DSS agent name (or id)

# Schemas
STRUCT_COLS = ["memo_id", "title", "description", "metrics"]
MEMO_COLS = ["memo_id", "title", "content"]


def init_config():
    """Load .env for local dev (no-op in DSS)."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
