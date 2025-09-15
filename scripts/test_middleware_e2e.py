#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from ai_simple_research_pipeline.http_server import (
    start_test_http_server,
    stop_test_http_server,
)

# ----------------- helpers -----------------


def load_env_value(key: str, default: str | None = None) -> str:
    """Read a single value from .env (no extra deps)."""
    if key in os.environ:
        return os.environ[key]

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()

    if default is not None:
        return default
    raise KeyError(f"{key} not found in environment or .env")


def guess_webhook_host_for_other_containers() -> str:
    """
    We need a hostname that other containers on the same Docker network
    (e.g., 'prefect-middleware') can reach.

    Preferred: the devcontainer service name from .devcontainer/docker-compose.yml:
        ai-simple-research-pipeline
    We test-resolve it; if not resolvable, fall back to our container IP on the
    route to 'prefect-middleware'.
    You can override by setting WEBHOOK_HOST.
    """
    override = os.environ.get("WEBHOOK_HOST")
    if override:
        return override

    candidate = "ai-simple-research-pipeline"
    try:
        socket.gethostbyname(candidate)
        return candidate
    except socket.gaierror:
        pass

    # Fallback: determine our IP on the path to the middleware container
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("prefect-middleware", 4080))  # doesn't actually send packets
            ip = s.getsockname()[0]
            return ip
    except Exception:
        # Absolute last resort—should work if all in one host namespace
        return "127.0.0.1"


TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "CRASHED"}


# ----------------- main test -----------------


async def main() -> int:
    api_key = load_env_value("PREFECT_MIDDLEWARE_API_KEY")
    middleware_base = os.environ.get("MIDDLEWARE_URL", "http://prefect-middleware:4080")
    deployment_name = os.environ.get("DEPLOYMENT_NAME", "research_pipeline")

    # 1) Start the test HTTP server (bind to 0.0.0.0 so others can reach it)
    #    We won't use the returned base URL for webhooks because it will be http://0.0.0.0:8000.
    host_for_bind = "0.0.0.0"
    port = 8000
    base_bound, srv, thread = start_test_http_server(
        host=host_for_bind,
        port=port,
        inputs_dir="projects/privateai/user_input",
        outputs_dir="projects/privateai/http_server_outputs",
        add_content_disposition=True,
    )
    # Give it a moment to start
    time.sleep(0.2)

    # 2) Compute a webhook base that other containers can reach
    webhook_host = guess_webhook_host_for_other_containers()
    print(f"Webhook host: {webhook_host}")
    webhook_base = f"http://{webhook_host}:{port}"

    # 3) Build parameters equivalent to research_pipeline.py example
    parameters: dict[str, Any] = {
        "project_name": "privateai",
        "documents": "",  # it will create a new bucket automatically
        "flow_options": {
            "input_documents_urls": [f"{webhook_base}/inputs/privateai_project_description.pdf"],
            "output_documents_urls": {
                "full_report.md": f"{webhook_base}/outputs/full_report.md",
                "short_report.md": f"{webhook_base}/outputs/short_report.md",
                "initial_summary.json": f"{webhook_base}/outputs/initial_summary.json",
                "short_description.md": f"{webhook_base}/outputs/short_description.md",
                "long_description.md": f"{webhook_base}/outputs/long_description.md",
            },
            "report_webhook_url": f"{webhook_base}/webhook/report",
            "status_webhook_url": f"{webhook_base}/webhook/status",
        },
    }

    headers = {"x-api-key": api_key, "content-type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        # 4) Smoke test: list deployments
        r = await client.get(f"{middleware_base}/deployments", headers=headers)
        r.raise_for_status()
        deployments = r.json()
        print("---- /deployments ----")
        print(json.dumps(deployments, indent=2))

        # sanity: ensure target deployment exists
        names = {d["name"] for d in deployments}
        if deployment_name not in names:
            raise RuntimeError(
                f"Deployment '{deployment_name}' not found. Available: {sorted(names)}"
            )

        # 5) Trigger run by NAME
        r = await client.post(
            f"{middleware_base}/deployments/{deployment_name}/runs",
            headers=headers,
            content=json.dumps({"parameters": parameters, "tags": ["e2e", "devcontainer"]}),
        )
        r.raise_for_status()
        flow_run_id = r.json()["flow_run_id"]
        print(f"Triggered flow_run_id={flow_run_id}")
        print(f"Flow run:\n{json.dumps(r.json(), indent=2)}")

        # 6) Poll status until terminal
        print("---- polling /runs/{id} ----")
        poll_every = float(os.environ.get("POLL_EVERY", "30"))
        started = time.time()
        last_state = None

        while True:
            rs = await client.get(f"{middleware_base}/runs/{flow_run_id}", headers=headers)
            rs.raise_for_status()
            payload = rs.json()
            print(f"Payload:\n{json.dumps(payload, indent=2)}")
            state_type = (payload.get("state_type") or "").upper()
            state_name = payload.get("state_name")
            if state_type != last_state:
                print(f"[{time.strftime('%X')}] state={state_type} ({state_name})")
                last_state = state_type

            if state_type in TERMINAL_STATES:
                print("Terminal state reached.")
                break

            await asyncio.sleep(poll_every)

        elapsed = time.time() - started
        print(f"Done in {elapsed:.1f}s")

    # 7) Shutdown test server
    stop_test_http_server(srv)
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        exit_code = 130
    sys.exit(exit_code)
