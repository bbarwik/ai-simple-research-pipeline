# Integrating with the Prefect Middleware (HTTP API)

Our middleware is a thin FastAPI wrapper around Prefect. It exposes 3 endpoints:

* `GET /deployments` — list deployments (now includes default `parameters` and `parameter_openapi_schema`)
* `POST /deployments/{deployment_name}/runs` — start a flow **by deployment name**
* `GET /runs/{flow_run_id}` — fetch the full flow-run payload & state

It uses **API-key auth** and expects **Google Cloud Storage Signed URLs** for input/output files.

---

## Authentication

Send **one** of the following:

* Header: `x-api-key: <YOUR_KEY>`
* Header: `Authorization: Bearer <YOUR_KEY>`

> The key is read from `PREFECT_MIDDLEWARE_API_KEY` in the middleware’s environment.

---

## Base URL

* From **outside** Docker: `http://<host-ip-or-dns>:4080`
* From **inside** the compose network: `http://prefect-middleware:4080`

---

## Endpoints

### 1) List deployments

**Request**

```
GET /deployments
Headers:
  x-api-key: <YOUR_KEY>
```

**Response** (abridged)

```json
[
  {
    "id": "…",
    "name": "research_pipeline",
    "flow_id": "…",
    "paused": false,
    "parameters": {},
    "parameter_openapi_schema": {
      "type": "object",
      "required": ["project_name","documents","flow_options"],
      "properties": {
        "project_name": {"type":"string"},
        "documents": {"type":"string"},
        "flow_options": { /* see below */ }
      }
    }
  }
]
```

Use `parameter_openapi_schema` to learn what’s required for the run.

---

### 2) Start a run (by deployment name)

**Request**

```
POST /deployments/{deployment_name}/runs
Headers:
  x-api-key: <YOUR_KEY>
Body:
  { "parameters": {…}, "tags": ["optional"], "idempotency_key": "optional" }
```

For the **main orchestration** (`research_pipeline`), the `parameters` object must include:

```json
{
  "project_name": "my_project",
  "documents": "projects/my_project",   // or a gs:// path
  "flow_options": {
    "input_documents_urls": [
      "https://storage.googleapis.com/…?X-Goog-Signature=…"
    ],
    "output_documents_urls": {
      "final_report.md": "https://storage.googleapis.com/…?X-Goog-Signature=…",
      "initial_summary.json": "https://storage.googleapis.com/…?X-Goog-Signature=…"
    },
    "report_webhook_url": "https://yourapp.example.com/webhook/report",
    "status_webhook_url": "https://yourapp.example.com/webhook/status"
  }
}
```

> **Signed URLs**
>
> * Generate **V4 Signed URLs** for each input file you want the flow to read.
> * Provide **writeable Signed URLs** (e.g., `PUT` method) for each expected output.
> * If your storage requires custom headers for `PUT`, you can pass the richer form instead of a plain string:
>
>   ```json
>   "output_documents_urls": {
>     "final_report.md": "https://…",
>     "initial_summary.json": {
>       "url": "https://…",
>       "headers": { "x-goog-meta-foo": "bar" }
>     }
>   }
>   ```

**Response**

```json
{ "flow_run_id": "c27dcf73-3d9d-4273-89c0-33e2977c3f3f" }
```

---

### 3) Get run status

**Request**

```
GET /runs/{flow_run_id}
Headers:
  x-api-key: <YOUR_KEY>
```

**Response** (full Prefect `FlowRun`, e.g.)

```json
{
  "id": "c27d…3f3f",
  "name": "research_pipeline-my_project",
  "parameters": { /* exactly what you sent */ },
  "state_type": "RUNNING",
  "state_name": "Running",
  "state": { "type": "RUNNING", "name": "Running", ... },
  "start_time": "2025-09-15T08:19:21.013620Z",
  "end_time": null,
  ...
}
```

Terminal states include `COMPLETED`, `FAILED`, `CANCELLED`, `CRASHED`.

---

## End-to-End Examples

### cURL (quick smoke)

```bash
API=http://localhost:4080
KEY=$(grep ^PREFECT_MIDDLEWARE_API_KEY= .env | cut -d= -f2-)

# 1) list
curl -s -H "x-api-key: $KEY" "$API/deployments" | jq

# 2) start research_pipeline
curl -s -X POST "$API/deployments/research_pipeline/runs" \
  -H "x-api-key: $KEY" -H "content-type: application/json" \
  -d @- <<'JSON' | tee /tmp/run.json
{
  "parameters": {
    "project_name": "my_project",
    "documents": "projects/my_project",
    "flow_options": {
      "input_documents_urls": [
        "https://storage.googleapis.com/your-bucket/user_input/pitch_deck.pdf?X-Goog-Algorithm=GOOG4-RSA-SHA256&..."
      ],
      "output_documents_urls": {
        "final_report.md": "https://storage.googleapis.com/your-bucket/final_report/final_report.md?X-Goog-Algorithm=GOOG4-RSA-SHA256&...",
        "initial_summary.json": "https://storage.googleapis.com/your-bucket/initial_summary/initial_summary.json?X-Goog-Algorithm=GOOG4-RSA-SHA256&..."
      },
      "report_webhook_url": "https://yourapp.example.com/webhook/report",
      "status_webhook_url": "https://yourapp.example.com/webhook/status"
    }
  },
  "tags": ["api"]
}
JSON

RUN_ID=$(jq -r .flow_run_id </tmp/run.json)

# 3) poll
watch -n 5 "curl -s -H 'x-api-key: $KEY' $API/runs/$RUN_ID | jq '.state_type, .state_name, .start_time, .end_time'"
```

---

## JavaScript Integration

Below are minimal examples using **Node 18+** (native `fetch`). Adapt for your framework as needed.

### Setup helpers

```js
// scripts/mw.js
const API = process.env.MIDDLEWARE_URL || "http://localhost:4080";
const API_KEY = process.env.PREFECT_MIDDLEWARE_API_KEY;

if (!API_KEY) {
  throw new Error("Set PREFECT_MIDDLEWARE_API_KEY in your env");
}

function headers(json = true) {
  const h = { "x-api-key": API_KEY };
  if (json) h["content-type"] = "application/json";
  return h;
}

export { API, headers };
```

### List deployments

```js
// scripts/list.js
import { API, headers } from "./mw.js";

const res = await fetch(`${API}/deployments`, { headers: headers(false) });
if (!res.ok) {
  console.error("List deployments failed:", await res.text());
  process.exit(1);
}
const deployments = await res.json();
console.log(JSON.stringify(deployments, null, 2));
```

### Trigger run with GCS Signed URLs

```js
// scripts/trigger.js
import { API, headers } from "./mw.js";

const body = {
  parameters: {
    project_name: "my_project",
    documents: "projects/my_project",
    flow_options: {
      input_documents_urls: [
        "https://storage.googleapis.com/your-bucket/user_input/doc.pdf?X-Goog-Algorithm=GOOG4-RSA-SHA256&..."
      ],
      output_documents_urls: {
        "final_report.md": "https://storage.googleapis.com/your-bucket/final_report/final_report.md?X-Goog-Algorithm=GOOG4-RSA-SHA256&..."
      },
      report_webhook_url: "https://yourapp.example.com/webhook/report",
      status_webhook_url: "https://yourapp.example.com/webhook/status"
    }
  },
  tags: ["node-client"]
};

const res = await fetch(`${API}/deployments/research_pipeline/runs`, {
  method: "POST",
  headers: headers(),
  body: JSON.stringify(body)
});
if (!res.ok) {
  console.error("Trigger failed:", res.status, await res.text());
  process.exit(1);
}
const { flow_run_id } = await res.json();
console.log("flow_run_id:", flow_run_id);
```

### Poll until terminal

```js
// scripts/poll.js
import { API, headers } from "./mw.js";

const flowRunId = process.argv[2];
if (!flowRunId) {
  console.error("Usage: node scripts/poll.js <flow_run_id>");
  process.exit(1);
}

const terminal = new Set(["COMPLETED", "FAILED", "CANCELLED", "CRASHED"]);

while (true) {
  const res = await fetch(`${API}/runs/${flowRunId}`, { headers: headers(false) });
  if (!res.ok) {
    console.error("Status failed:", await res.text());
    process.exit(1);
  }
  const payload = await res.json();
  console.log(`[${new Date().toISOString()}]`, payload.state_type, payload.state_name);
  if (terminal.has((payload.state_type || "").toUpperCase())) break;
  await new Promise(r => setTimeout(r, 5000));
}
```

---

## Python Integration

Using `httpx` (async) for reliability.

```python
# client_middleware.py
from __future__ import annotations
import os, asyncio, json
import httpx

API = os.getenv("MIDDLEWARE_URL", "http://localhost:4080")
API_KEY = os.getenv("PREFECT_MIDDLEWARE_API_KEY")
if not API_KEY:
    raise RuntimeError("Set PREFECT_MIDDLEWARE_API_KEY in your environment")

HEADERS_JSON = {"x-api-key": API_KEY, "content-type": "application/json"}
HEADERS = {"x-api-key": API_KEY}

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "CRASHED"}

async def list_deployments():
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{API}/deployments", headers=HEADERS)
        r.raise_for_status()
        return r.json()

async def trigger_research_pipeline(
    project_name: str,
    documents: str,
    input_signed_urls: list[str],
    output_signed_urls: dict[str, str],
    report_webhook: str = "",
    status_webhook: str = "",
    tags: list[str] = None,
):
    body = {
        "parameters": {
            "project_name": project_name,
            "documents": documents,
            "flow_options": {
                "input_documents_urls": input_signed_urls,
                "output_documents_urls": output_signed_urls,
                "report_webhook_url": report_webhook,
                "status_webhook_url": status_webhook,
            },
        },
        "tags": tags or [],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{API}/deployments/research_pipeline/runs",
            headers=HEADERS_JSON,
            content=json.dumps(body),
        )
        r.raise_for_status()
        return r.json()["flow_run_id"]

async def wait_for_terminal(flow_run_id: str, interval: float = 5.0):
    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            r = await client.get(f"{API}/runs/{flow_run_id}", headers=HEADERS)
            r.raise_for_status()
            payload = r.json()
            print(payload.get("state_type"), payload.get("state_name"))
            if (payload.get("state_type") or "").upper() in TERMINAL:
                return payload
            await asyncio.sleep(interval)
```

---

## Parameter Reference (what to send)

### For `research_pipeline`

| Field                                | Type      | Required                                               | Description                                                                                       |
| ------------------------------------ | --------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `project_name`                       | string    | ✅                                                      | Project identifier (used for naming & paths)                                                      |
| `documents`                          | string    | ✅                                                      | Local folder (e.g., `projects/my_project`) or a storage base (e.g., `gs://…`)                     |
| `flow_options.input_documents_urls`  | string\[] | ✅ if you want the pipeline to **download** your inputs | GCS **Signed URLs** (`GET`) for the raw input files to analyze                                    |
| `flow_options.output_documents_urls` | object    | optional but recommended                               | Map of expected output filenames → GCS **Signed URLs** (`PUT`) so the pipeline can upload results |
| `flow_options.report_webhook_url`    | string    | optional                                               | Receives a final artifacts summary payload                                                        |
| `flow_options.status_webhook_url`    | string    | optional                                               | Receives Prefect status webhooks throughout the run                                               |

**Common output names** you can pre-sign:

* `final_report.md`
* `initial_summary.json`
* `standardized_file/*.md` (dynamic per input)
* `review_finding/risks.json`
* `review_finding/opportunities.json`
* `review_finding/questions.json`

(You can always inspect what got produced by polling `/runs/{id}` and by looking at your webhook payloads.)

---

## Generating GCS Signed URLs (quick pointers)

You’ll typically pre-generate:

* **GET** Signed URLs for **each input** file you want the pipeline to read.
* **PUT** Signed URLs for **each output** path you want the pipeline to write.

Consider:

* Expiration long enough for your flow duration.
* If you need custom metadata/headers on upload, use the extended `{"url": "...","headers": {...}}` shape for `output_documents_urls`.

> See Google’s “Signed URLs” docs for exact commands and SDK snippets.

---

## Webhooks

If you provide `status_webhook_url`, the middleware’s underlying Prefect hooks will POST status changes as JSON.
`report_webhook_url` receives a summary with newly created documents at the end of the run.

Ensure your endpoints are accessible from within the Docker network (or exposed publicly) and accept `application/json`.

---

## Error Handling

* `401 Unauthorized` → bad/missing API key
* `404 Not Found` → deployment name typo
* `409 Conflict` → duplicate deployment names detected (rename/qualify)
* `5xx` → Prefect/middleware internal error — check logs

When triggering runs, the middleware returns only the `flow_run_id`. Use `/runs/{id}` to observe progress or to build your own awaiter.

---

## Tips

* Always **read `/deployments` first** to confirm the parameter schema and required fields for the specific deployment.
* Use **idempotency keys** in `POST /runs` if your client may retry.
* Prefer **server-reachable** webhook URLs and storage endpoints; from another container, DNS service names (e.g., `your-service:port`) are usually best.
