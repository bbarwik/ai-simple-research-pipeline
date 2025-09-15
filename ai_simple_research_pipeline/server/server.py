from __future__ import annotations

import os
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from prefect import get_client
from pydantic import BaseModel, Field

# ---------- Auth dependency ----------

API_KEY_ENV = "PREFECT_MIDDLEWARE_API_KEY"


async def require_api_key(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    """Accepts either Authorization: Bearer <key> or x-api-key: <key>."""
    required = os.getenv(API_KEY_ENV, "")
    if not required:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Server not configured; set {API_KEY_ENV} in environment.",
        )

    provided = None
    if x_api_key:
        provided = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided = authorization.split(" ", 1)[1].strip()

    if provided != required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


# ---------- Schemas ----------


class DeploymentItem(BaseModel):
    id: UUID
    name: str
    flow_id: UUID
    flow_name: Optional[str] = None
    paused: Optional[bool] = None
    work_pool_name: Optional[str] = None
    work_queue_name: Optional[str] = None

    # New: surface parameters + schema so clients know what to send
    parameters: dict[str, Any] = Field(default_factory=dict)
    parameter_openapi_schema: Optional[dict[str, Any]] = None


class TriggerRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    idempotency_key: Optional[str] = None


class TriggerResponse(BaseModel):
    flow_run_id: UUID


# ---------- App ----------

app = FastAPI(title="Prefect Middleware", version="1.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"ok": "true"}


@app.get(
    "/deployments", response_model=list[DeploymentItem], dependencies=[Depends(require_api_key)]
)
async def list_deployments(limit: int | None = 100) -> list[DeploymentItem]:
    """List deployments (now including their parameters + schema)."""
    async with get_client() as client:
        deployments = await client.read_deployments(limit=limit)
        items: list[DeploymentItem] = []
        for d in deployments:
            items.append(
                DeploymentItem(
                    id=d.id,
                    name=d.name,
                    flow_id=d.flow_id,
                    flow_name=getattr(d, "flow_name", None),
                    paused=getattr(d, "paused", None),
                    work_pool_name=getattr(d, "work_pool_name", None),
                    work_queue_name=getattr(d, "work_queue_name", None),
                    parameters=getattr(d, "parameters", {}) or {},
                    parameter_openapi_schema=getattr(d, "parameter_openapi_schema", None),
                )
            )
        return items


@app.post(
    "/deployments/{deployment_name}/runs",
    response_model=TriggerResponse,
    dependencies=[Depends(require_api_key)],
)
async def start_deployment_run(deployment_name: str, body: TriggerRequest) -> TriggerResponse:
    """
    Trigger a new flow run by *deployment name* (e.g. 'report_flow').

    Implementation detail:
    - We resolve the name by scanning deployments for an exact name match.
      This avoids requiring '<FLOW_NAME>/<DEPLOYMENT_NAME>' format and works with your
      current deployment names ('report_flow', 'summary_flow', etc.).
    """
    async with get_client() as client:
        # Resolve name -> id (exact match on DeploymentResponse.name)
        deployments = await client.read_deployments(limit=200)
        matches = [d for d in deployments if d.name == deployment_name]
        if not matches:
            raise HTTPException(status_code=404, detail=f"Deployment '{deployment_name}' not found")
        if len(matches) > 1:
            # Extremely rare, but better to be explicit
            raise HTTPException(
                status_code=409,
                detail=f"Multiple deployments named '{deployment_name}' found; disambiguate.",
            )
        deployment = matches[0]

        fr = await client.create_flow_run_from_deployment(
            deployment_id=deployment.id,
            parameters=body.parameters or {},
            tags=body.tags or [],
            idempotency_key=body.idempotency_key,
        )
        return TriggerResponse(flow_run_id=fr.id)


@app.get(
    "/runs/{flow_run_id}",
    response_model=dict,  # Return the full FlowRun as JSON
    dependencies=[Depends(require_api_key)],
)
async def get_run_status(flow_run_id: UUID) -> dict[str, Any]:
    """
    Return the complete FlowRun payload (all fields), including:
      - name, flow_id, state_id, deployment_id, deployment_version
      - work_queue_name, flow_version, parameters, idempotency_key, context
      - policy, tags, labels, parent_task_run_id, run_count
      - expected/next/start/end times, run time estimates
      - infra/doc IDs and PIDs, created_by, work_pool/queue fields
      - state/state_type/state_name, job_variables, etc.

    We use Prefect's model serialization for a faithful JSON representation.
    """
    async with get_client() as client:
        fr = await client.read_flow_run(flow_run_id)
        # Prefect models provide pydantic serialization compatible with JSON
        return fr.model_dump(mode="json")
