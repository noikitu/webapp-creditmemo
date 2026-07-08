"""Local dev runner. Requires webaiku + a DSS connection. Run:
    VITE_API_PORT=5000 python -m credit_memo.backend.wsgi_local
"""
import os

from .config import init_config

init_config()

from flask import Flask  # noqa: E402
from flask_cors import CORS  # noqa: E402
from webaiku.extension import WEBAIKU  # noqa: E402

from .api.memo_api import memo_api  # noqa: E402

app = Flask(__name__)
CORS(app)

_port = int(os.getenv("VITE_API_PORT", "5000"))
WEBAIKU(app, "webapps/credit_memo", _port)
WEBAIKU.extend(app, [memo_api])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=_port, debug=True)
