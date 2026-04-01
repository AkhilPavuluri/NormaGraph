"""Run the standard FastAPI app: ``python -m backend`` from the repository root."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    print(f"NormaGraph API — http://localhost:{port}/  (GET /health, GET /docs)")
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
