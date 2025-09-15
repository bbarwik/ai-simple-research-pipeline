import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import time as _now
from typing import Any, cast

from ai_pipeline_core import get_pipeline_logger

logger = get_pipeline_logger(__name__)


class _TestHTTPState:
    """Holds in-memory state for the simple test server."""

    def __init__(self, inputs_dir: Path, outputs_dir: Path):
        self.inputs_dir = inputs_dir
        self.outputs_dir = outputs_dir
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.last_status: dict[str, Any] | None = None
        self.last_report: dict[str, Any] | None = None


def _safe_name(name: str) -> str:
    return Path(name).name  # prevent path traversal


class _TestHTTPServer(ThreadingHTTPServer):
    """Custom server with state and configuration."""

    state: _TestHTTPState
    add_content_disposition: bool


class _TestHTTPRequestHandler(BaseHTTPRequestHandler):
    # The server attribute is dynamically assigned by HTTPServer
    # We know it will be our _TestHTTPServer type at runtime

    def _send_json(self, obj: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, data: bytes, content_type: str | None, filename: str | None) -> None:
        server = cast(_TestHTTPServer, self.server)
        ct = (content_type or "application/octet-stream").split(";")[0]
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        if server.add_content_disposition and filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        server = cast(_TestHTTPServer, self.server)
        if self.path.startswith("/inputs/"):
            rel = _safe_name(self.path.split("/inputs/", 1)[1])
            file_path = server.state.inputs_dir / rel
            if not file_path.exists():
                self._send_json({"error": "not found", "path": rel}, status=404)
                return
            data = file_path.read_bytes()
            content_type, _ = mimetypes.guess_type(str(file_path))
            self._send_bytes(data, content_type, rel)
            return

        if self.path == "/__dump":
            outputs = []
            for p in sorted(server.state.outputs_dir.glob("*")):
                if p.is_file():
                    outputs.append(
                        {
                            "name": p.name,
                            "size": p.stat().st_size,
                            "mtime": int(p.stat().st_mtime),
                        }
                    )
            self._send_json(
                {
                    "outputs": outputs,
                    "last_status": server.state.last_status,
                    "last_report": server.state.last_report,
                }
            )
            return

        self._send_json({"ok": True, "message": "test server running"}, status=200)

    def do_POST(self) -> None:
        server = cast(_TestHTTPServer, self.server)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""

        if self.path == "/webhook/status":
            status_data: dict[str, Any]
            try:
                status_data = json.loads(body or b"{}")
            except Exception:
                status_data = {"raw": body.decode("utf-8", "replace")}
            server.state.last_status = {"received_at": int(_now()), "data": status_data}
            (server.state.outputs_dir / f"status-{int(_now())}.json").write_bytes(
                json.dumps(server.state.last_status, indent=2).encode("utf-8")
            )
            self._send_json({"ok": True})
            return

        if self.path == "/webhook/report":
            report_data: dict[str, Any]
            try:
                report_data = json.loads(body or b"{}")
            except Exception:
                report_data = {"raw": body.decode("utf-8", "replace")}
            server.state.last_report = {"received_at": int(_now()), "data": report_data}
            (server.state.outputs_dir / f"report-{int(_now())}.json").write_bytes(
                json.dumps(server.state.last_report, indent=2).encode("utf-8")
            )
            self._send_json({"ok": True})
            return

        if self.path == "/__reset":
            for p in server.state.outputs_dir.glob("*"):
                try:
                    if p.is_file():
                        p.unlink()
                except Exception:
                    pass
            server.state.last_status = None
            server.state.last_report = None
            self._send_json({"ok": True, "message": "reset"})
            return

        self._send_json({"error": "unknown endpoint", "path": self.path}, status=404)

    def do_PUT(self) -> None:
        server = cast(_TestHTTPServer, self.server)
        if not self.path.startswith("/outputs/"):
            self._send_json({"error": "unknown endpoint", "path": self.path}, status=404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else b""
        rel = _safe_name(self.path.split("/outputs/", 1)[1])
        out_path = server.state.outputs_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)

        meta = {
            "received_at": int(_now()),
            "headers": {k: v for k, v in self.headers.items()},
            "size": len(data),
        }
        (server.state.outputs_dir / (rel + ".meta.json")).write_bytes(
            json.dumps(meta, indent=2).encode("utf-8")
        )

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')


def start_test_http_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    inputs_dir: str | Path = "test_server_inputs",
    outputs_dir: str | Path = "test_server_outputs",
    add_content_disposition: bool = True,
) -> tuple[str, _TestHTTPServer, threading.Thread]:
    state = _TestHTTPState(Path(inputs_dir), Path(outputs_dir))

    httpd = _TestHTTPServer((host, port), _TestHTTPRequestHandler)
    # attach state & config to the *server*
    httpd.state = state  # <— critical
    httpd.add_content_disposition = add_content_disposition

    t = threading.Thread(target=httpd.serve_forever, name="test-http-server", daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    logger.info(f"Test HTTP server running at {base_url}")
    logger.info(f"Inputs dir: {state.inputs_dir.resolve()}")
    logger.info(f"Outputs dir: {state.outputs_dir.resolve()}")
    return base_url, httpd, t


def stop_test_http_server(server: _TestHTTPServer) -> None:
    """Stop the test HTTP server started by start_test_http_server()."""
    try:
        server.shutdown()
    finally:
        server.server_close()
    logger.info("Test HTTP server stopped.")
