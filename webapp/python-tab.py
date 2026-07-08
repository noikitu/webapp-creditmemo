# DSS webapp — Python tab (the entire content). `app` is injected by DSS.
from credit_memo.backend.wsgi_dss import init_dss_app

init_dss_app(app)  # noqa: F821 — `app` is provided by DSS
