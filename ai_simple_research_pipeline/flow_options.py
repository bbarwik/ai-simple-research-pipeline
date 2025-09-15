from ai_pipeline_core import FlowOptions, ModelName
from pydantic import Field


class ProjectFlowOptions(FlowOptions):
    """Project-specific flow configuration for startup analysis pipeline."""

    core_model: ModelName = Field(default="google/gemini-2.5-flash")
    small_model: ModelName = Field(default="google/gemini-2.5-flash-lite")

    # bellow 2 fields are for GCS signed urls
    input_documents_urls: list[str] = Field(
        default=[], description="List of input documents (http urls) to use for the pipeline"
    )
    output_documents_urls: dict[str, str] = Field(
        default={},
        description=(
            "Map output file name -> either a signed URL string or "
            "a dict {'url': str, 'headers': dict[str,str]} for header overrides"
        ),
    )

    report_webhook_url: str = Field(
        default="", description="Webhook URL to send the report and other files to"
    )
    status_webhook_url: str = Field(
        default="", description="Webhook URL to send the status of prefect flow runs to"
    )
