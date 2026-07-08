"""Project-specific configuration for the Credit Memo webapp.

These values differ between DSS projects (a copied project often renames
datasets while keeping managed-folder IDs) — verify against the target with
`dku dataset list` / `dku managed-folder list` before deploying.
"""

# Datasets
DATASET_NAME = "structure_memo"   # memo_id, title, description, metrics
MEMO_DATASET = "credit_memo"      # memo_id, title, content (agent output)
METRICS_DATASET = "metrics"       # metric, description (selectable catalog)

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
