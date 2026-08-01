"""Field Kit — HTTP server for the personal tooling index.

    py server/app.py            # serve API + built front end on :8765
    py server/app.py --reload   # reload on file change (dev)

Endpoints
    GET  /api/catalog                 category tree + every tool (no source)
    GET  /api/tools/{id}              one tool, with its source code
    POST /api/tools/{id}/run          run it, get result blocks back
    POST /api/reload                  re-scan the tools package
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _load_dotenv() -> str | None:
    """Read KEY=VALUE lines from a .env into the process environment.

    Tool modules read their config from os.environ at import time, so this must
    run before the registry imports them (i.e. before registry.load()). A real
    environment variable always wins — anything docker compose already injected
    is left untouched — so this only fills gaps for local or non-compose runs.
    Returns a short description of what it loaded, or None if no file was found.
    """
    candidates = [
        BASE_DIR.parent / ".env",   # repo root — local dev
        Path.cwd() / ".env",
        Path("/opt/tools/.env"),    # container deploy dir, if run outside compose
    ]
    for path in candidates:
        try:
            if not path.is_file():
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        loaded = 0
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:   # never override a real env var
                os.environ[key] = value
                loaded += 1
        return f"{path} ({loaded} new var(s))"
    return None


_DOTENV_SOURCE = _load_dotenv()

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from registry import registry
from toolkit import InputError, Result, ToolError, coerce_params

DIST_DIR = BASE_DIR.parent / "frontend" / "dist"
RUNNER = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool")

@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    if _DOTENV_SOURCE:
        print(f"[field-kit] env loaded from {_DOTENV_SOURCE}")
    else:
        print("[field-kit] no .env file found — using process env / defaults")
    registry.load()
    print(f"[field-kit] {len(registry.tools)} tool(s) loaded")
    for err in registry.errors:
        print(f"[field-kit] !! {err['module']}: {err['error'].strip().splitlines()[-1]}")
    yield


app = FastAPI(title="Field Kit", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Headers the nginx layer would have added. We serve straight from uvicorn,
    so they live here instead."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.get("/healthz", include_in_schema=False)
def healthz() -> PlainTextResponse:
    """Liveness probe hit by the Docker HEALTHCHECK, the CI smoke test and Uptime
    Kuma. Must return the literal body 'ok' — the deploy workflow greps for it."""
    return PlainTextResponse("ok")


# --------------------------------------------------------------------------
# api
# --------------------------------------------------------------------------

@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    return registry.catalog()


@app.get("/api/tools/{tool_id}")
def get_tool(tool_id: str) -> dict[str, Any]:
    tool = registry.get(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"No tool with id {tool_id!r}")
    return tool.to_dict(with_source=True)


@app.post("/api/tools/{tool_id}/run")
def run_tool(tool_id: str, payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    tool = registry.get(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"No tool with id {tool_id!r}")

    try:
        params = coerce_params(tool, payload.get("params", {}))
    except InputError as exc:
        return JSONResponse(status_code=422, content=_input_fault(exc))

    started = time.perf_counter()
    future = RUNNER.submit(_invoke, tool, params)
    try:
        result, stdout = future.result(timeout=tool.timeout)
    except FutureTimeout:
        return JSONResponse(
            status_code=504,
            content={"ok": False, "kind": "timeout",
                     "error": f"Timed out after {tool.timeout:g}s."},
        )
    except ToolError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "kind": "tool", "error": exc.message, "detail": exc.detail},
        )
    except InputError as exc:
        return JSONResponse(status_code=422, content=_input_fault(exc))
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "kind": "crash", "error": f"{type(exc).__name__}: {exc}",
                     "detail": traceback.format_exc()},
        )

    elapsed = (time.perf_counter() - started) * 1000
    return JSONResponse({
        "ok": True,
        "result": result.to_dict(),
        "stdout": stdout,
        "elapsed_ms": round(elapsed, 2),
    })


def _input_fault(exc: InputError) -> dict[str, Any]:
    return {"ok": False, "kind": "input", "error": exc.message,
            "field": exc.field_id, "index": exc.index}


def _invoke(tool, params: dict[str, Any]) -> tuple[Result, str]:
    """Run the tool with stdout captured, so ``print`` in a script still shows up."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = tool.run(params)
    if not isinstance(result, Result):
        wrapped = Result()
        if result is None:
            wrapped.notice("The tool returned nothing.", "warn")
        elif isinstance(result, str):
            wrapped.text(result)
        else:
            wrapped.json(result)
        result = wrapped
    return result, buffer.getvalue()


@app.post("/api/reload")
def reload_tools() -> dict[str, Any]:
    registry.load()
    return {"ok": True, "tools": len(registry.tools), "errors": registry.errors}


# --------------------------------------------------------------------------
# static front end (built with `npm run build` in ../frontend)
# --------------------------------------------------------------------------

_PLACEHOLDER = """<!doctype html><meta charset="utf-8"><title>Field Kit</title>
<body style="background:#f6f5f1;color:#1e3a5f;font:14px/1.6 monospace;padding:60px;max-width:60ch">
<h1 style="font-size:28px">FIELD KIT — front end not built</h1>
<p>The API is up. Build the interface, then reload:</p>
<pre style="border:1px solid #1e3a5f;padding:16px">cd frontend
npm install
npm run build</pre>
<p>Or run the dev server with <code>npm run dev</code> and open
<a href="http://localhost:5173" style="color:#b4451f">localhost:5173</a>.</p>
<p><a href="/api/docs" style="color:#b4451f">/api/docs</a></p>
</body>"""

if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = (DIST_DIR / full_path).resolve()
    if full_path and candidate.is_file() and candidate.is_relative_to(DIST_DIR.resolve()):
        return FileResponse(candidate)
    index = DIST_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(_PLACEHOLDER)


# --------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Field Kit tool server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reload", action="store_true", help="restart on source change")
    args = parser.parse_args()

    import uvicorn

    print(f"[field-kit] http://{args.host}:{args.port}")
    uvicorn.run(
        "app:app" if args.reload else app,
        host=args.host, port=args.port, reload=args.reload,
        reload_dirs=[str(BASE_DIR)] if args.reload else None,
    )


if __name__ == "__main__":
    main()
