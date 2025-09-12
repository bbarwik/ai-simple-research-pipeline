from ai_pipeline_core import (
    AIMessages,
    DocumentList,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)
from pydantic import BaseModel, ConfigDict, Field

from ai_simple_research_pipeline.documents.flow import InitialSummaryDocument

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


class FileDescriptor(BaseModel):
    """Descriptor for a single source file."""

    model_config = ConfigDict(frozen=True)

    name: str
    detected_type: str = Field(description="pitch_deck | whitepaper | blog | other")
    detected_language: str
    published_or_version_date: str | None = Field(default=None, description="YYYY-MM-DD if any")
    key_claims: list[str]
    data_points: list[str] = Field(description="numbers, metrics, TAM/SAM/SOM, KPIs")
    caveats: list[str] = Field(default_factory=list, description="limits/uncertainties")
    short_summary: str


class InitialSummary(BaseModel):
    """Initial due diligence summary structure."""

    model_config = ConfigDict(frozen=True)

    project_name: str
    long_summary: str
    sources: list[FileDescriptor]
    short_summary: str


@pipeline_task
async def create_initial_summary(
    documents: DocumentList, model: ModelName, project_name: str
) -> InitialSummaryDocument:
    """Create initial summary from user input documents."""
    prompt = prompt_manager.get("create_initial_summary", project_name=project_name)

    # Static context: all files (provider can cache)
    context = AIMessages(list(documents))
    messages = AIMessages([prompt])

    result = await llm.generate_structured(
        model,
        InitialSummary,
        context=context,
        messages=messages,
    )

    return InitialSummaryDocument.create(
        name=InitialSummaryDocument.FILES.INITIAL_SUMMARY,
        content=result.parsed,
    )
