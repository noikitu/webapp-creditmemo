# DSS entry point. The webapp's Python tab is just:
#     from credit_memo.backend.wsgi_dss import init_dss_app
#     init_dss_app(app)
# `app` is the Flask app DSS injects.
from webaiku.extension import WEBAIKU

from .api.memo_api import memo_api


def init_dss_app(app):
    """Serve the built SPA from dist/ and mount the API blueprints."""
    WEBAIKU(app, "webapps/credit_memo/dist")
    WEBAIKU.extend(app, [memo_api])
