from __future__ import annotations

import asyncio
import random
import re
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse

import httpx
from ai_pipeline_core import (
    DocumentList,
    FlowDocument,
    get_pipeline_logger,
    pipeline_task,
    prefect_test_harness,
    trace,
)
from ai_pipeline_core.prefect import flow
from ai_pipeline_core.storage import Storage
from ai_pipeline_core.storage.storage import GcsStorage
from prefect.client.schemas import State
from prefect.client.schemas.objects import FlowRun
from prefect.runtime import deployment, flow_run

from ai_simple_research_pipeline.flow_options import ProjectFlowOptions
from ai_simple_research_pipeline.flows import FLOWS
from ai_simple_research_pipeline.http_server import start_test_http_server, stop_test_http_server

logger = get_pipeline_logger(__name__)


@pipeline_task(retries=3, retry_delay_seconds=60, trace_ignore_inputs=["documents"])
async def send_report_webhook(webhook_url: str, project_name: str, documents: DocumentList):
    payload = {
        "project_name": project_name,
        "flow_run_id": flow_run.get_id(),
        "deployment_id": deployment.get_id(),
        "new_documents": [d.model_dump(mode="json") for d in documents],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(webhook_url, json=payload, follow_redirects=True)
        r.raise_for_status()


@pipeline_task(retries=3, retry_delay_seconds=60, trace_level="debug")
async def send_prefect_status(webhook_url: str, status: dict[str, Any]):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(webhook_url, json=status, follow_redirects=True)
        r.raise_for_status()


@pipeline_task(retries=3, retry_delay_seconds=60, trace_level="debug")
async def download_input_document(url: str) -> tuple[str, bytes]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()

        cd = r.headers.get("Content-Disposition", "")
        filename: Optional[str] = None

        m = re.search(r"""filename\*\s*=\s*UTF-8''([^;\r\n]+)""", cd, flags=re.I)
        if m:
            filename = unquote(m.group(1))
        else:
            m = re.search(r'filename\s*=\s*"([^"]+)"', cd, flags=re.I)
            filename = m.group(1) if m else Path(urlparse(str(r.request.url)).path).name or None

        if not filename:
            raise ValueError(f"No filename for url={url}, headers={dict(r.headers)}")

        filename = Path(filename).name  # prevent traversal
        logger.info(f"Downloaded {filename} ({len(r.content)} bytes)")
        return filename, r.content


@pipeline_task(retries=3, retry_delay_seconds=60, trace_level="debug")
async def upload_output_document(url: str, document: FlowDocument):
    headers = {"Content-Type": document.mime_type} if document.mime_type else {}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.put(url, content=document.content, headers=headers)
        r.raise_for_status()


@dataclass(slots=True)
class StatusWebhookHook:
    """Ordered, non-blocking status webhook sender for Prefect hooks."""

    project_name: str
    webhook_url: str
    _chain: Any = None  # internal sequencing

    async def __call__(self, _flow, fr: FlowRun, _state: State):
        if not self.webhook_url:
            return
        info = fr.model_dump(exclude={"parameters"}, mode="json")
        if "data" in info.get("state", {}):
            del info["state"]["data"]
        payload = {
            "project_name": self.project_name,
            "flow_run_id": str(fr.id),
            "deployment_id": deployment.get_id(),
            "data": info,
        }
        logger.info(f"Queueing status webhook -> {self.webhook_url}")
        self._chain = send_prefect_status.submit(
            self.webhook_url,
            payload,
            return_state=True,
            wait_for=[self._chain] if self._chain else None,  # enforce order
        )


@flow(name="research_pipeline", flow_run_name="research_pipeline-{project_name}", log_prints=True)
@trace(name="research_pipeline")
async def research_pipeline(project_name: str, documents: str, flow_options: ProjectFlowOptions):
    if not documents:
        base = re.sub(r"[^a-z0-9-]", "-", project_name.lower()).strip("-") or "project"
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        bucket = f"{base[:30]}-{datetime.now().strftime('%y-%m-%d')}-{random_suffix}"
        storage = GcsStorage(bucket)
        await storage.create_bucket()
        documents = storage.url_for("")
        logger.info(f"Created GCS bucket: {bucket}")

    if flow_options.input_documents_urls:
        doc_types = FLOWS[0].config.get_input_document_types()
        if len(doc_types) != 1:
            raise ValueError("Only one input document type is supported")
        storage = await Storage.from_uri(documents)
        target_base = storage.with_base(doc_types[0].canonical_name())
        results = await asyncio.gather(
            *[download_input_document(url) for url in flow_options.input_documents_urls]
        )
        for name, content in results:
            await target_base.write_bytes(name, content)

    status_hook = StatusWebhookHook(project_name, flow_options.status_webhook_url)

    new_docs: DocumentList = DocumentList()
    output_futures = []
    for idx, pipeline_flow in enumerate(FLOWS, start=1):
        logger.info(f"Starting flow {idx} of {len(FLOWS)}: {pipeline_flow.name}")
        current = await pipeline_flow.config.load_documents(documents)
        pipeline_flow_fn = pipeline_flow.with_options(
            retries=3,
            retry_delay_seconds=60,
            on_completion=[status_hook],
            on_failure=[status_hook],
            on_cancellation=[status_hook],
            on_crashed=[status_hook],
            on_running=[status_hook],
        )
        new_docs = await pipeline_flow_fn(project_name, current, flow_options)
        logger.info(f"Flow {pipeline_flow.name} produced {len(new_docs)} documents")
        await pipeline_flow.config.save_documents(documents, new_docs)
        for doc in new_docs:
            url = flow_options.output_documents_urls.get(doc.name)
            if url:
                output_futures.append(upload_output_document.submit(url, doc, return_state=False))

    if flow_options.report_webhook_url:
        await send_report_webhook(flow_options.report_webhook_url, project_name, new_docs)
    for future in output_futures:
        future.result(raise_on_failure=False)


if __name__ == "__main__":
    with prefect_test_harness():
        base, srv, thread = start_test_http_server(
            port=8000,
            inputs_dir="projects/privateai/user_input",
            outputs_dir="projects/http_server_outputs",
        )
        opts = ProjectFlowOptions(
            input_documents_urls=[f"{base}/inputs/privateai_project_description.pdf"],
            output_documents_urls={
                "full_report.md": f"{base}/outputs/full_report.md",
                "short_report.md": f"{base}/outputs/short_report.md",
                "short_description.md": f"{base}/outputs/short_description.md",
                "long_description.md": f"{base}/outputs/long_description.md",
                "initial_summary.json": f"{base}/outputs/initial_summary.json",
            },
            # Webhooks go to our server too
            status_webhook_url=f"{base}/webhook/status",
            report_webhook_url=f"{base}/webhook/report",
        )

        asyncio.run(
            research_pipeline(
                "privateai",
                "projects/privateai2",
                opts,
            )
        )
        stop_test_http_server(srv)
