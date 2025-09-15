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

from ai_simple_research_pipeline.documents.flow import StandardizedFileDocument

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


def slugify(name: str) -> str:
    """Convert a filename to a URL-safe slug."""
    base = Path(name).stem.lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "file"


@pipeline_task
async def standardize_content(
    document: Document,
    metadata: Document,
    model: ModelName,
    project_name: str,
) -> StandardizedFileDocument:
    """Convert document content to clean English Markdown.

    Args:
        document: User-provided file to standardize
        metadata: Extracted metadata for context
        model: Model to use for conversion
        project_name: Project name for context

    Returns:
        StandardizedFileDocument containing clean Markdown content
    """
    prompt = prompt_manager.get(
        "standardize_content",
        project_name=project_name,
        file_name=document.name,
    )

    # Use metadata as context for consistency
    context = AIMessages([metadata, document])
    messages = AIMessages([prompt])

    # Generate standardized Markdown
    result = await llm.generate(
        model=model,
        context=context,
        messages=messages,
    )

    # Create Markdown filename
    slug = slugify(document.name)
    md_name = f"{slug}.md"

    # Create content document
    content_doc = StandardizedFileDocument.create(
        name=md_name,
        content=result.content,
    )

    logger.debug(f"Standardized content for {document.name} -> {md_name}")
    return content_doc
