"""API launcher.

- Local dev:  `python run_api.py`            (set RELOAD=true for auto-reload)
- Production: platforms set $PORT; reload stays off. You can also run directly:
              `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
"""
from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "false").lower() in {"1", "true", "yes"},
        workers=int(os.environ.get("WEB_CONCURRENCY", "1")),
    )
