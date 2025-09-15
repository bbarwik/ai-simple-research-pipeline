import re
from pathlib import Path

from ai_pipeline_core import (
    AIMessages,
    Document,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)
from pydantic import BaseModel, ConfigDict, Field

from ai_simple_research_pipeline.documents.flow import StandardizedFileDocument

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


def slugify(name: str) -> str:
    """Convert a filename to a URL-safe slug."""
    base = Path(name).stem.lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "file"


class DocumentMetadata(BaseModel):
    """Metadata structure for standardized documents."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Precise, descriptive title from document content")
    original_filename: str = Field(description="Original file name")
    doc_type: str = Field(description="pitch_deck | whitepaper | blog | spec | other")
    published_or_version_date: str | None = Field(
        default=None, description="YYYY-MM-DD format if found"
    )
    language_detected: str = Field(description="Original language code (e.g., en, es, fr)")
    summary_improved: str = Field(description="3-6 sentence improved summary capturing key points")
    key_claims: list[str] = Field(description="Main claims or assertions")
    sources: list[str] = Field(
        default_factory=list, description="Internal references, links, or citations"
    )
    provenance_notes: str = Field(description="Brief explanation of how document was processed")


@pipeline_task
async def extract_metadata(
    document: Document,
    initial_summary: Document,
    model: ModelName,
    project_name: str,
) -> StandardizedFileDocument:
    """Extract structured metadata from a document.

    Args:
        document: User-provided file to analyze
        initial_summary: Initial project summary for context
        model: Model to use for extraction
        project_name: Project name for context

    Returns:
        StandardizedFileDocument containing YAML metadata
    """
    prompt = prompt_manager.get(
        "extract_metadata",
        project_name=project_name,
        file_name=document.name,
    )

    # Use initial summary as static context for caching
    context = AIMessages([initial_summary, document])
    messages = AIMessages([prompt])

    # Extract structured metadata
    result = await llm.generate_structured(
        model,
        DocumentMetadata,
        context=context,
        messages=messages,
    )

    # Create YAML filename
    slug = slugify(document.name)
    yaml_name = f"{slug}.yaml"

    # Create metadata document
    metadata_doc = StandardizedFileDocument.create(
        name=yaml_name,
        content=result.parsed,
    )

    logger.debug(f"Extracted metadata for {document.name} -> {yaml_name}")
    return metadata_doc
