import re
from pathlib import Path

from ai_pipeline_core import (
    AIMessages,
    DocumentList,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)

from ai_simple_research_pipeline.documents.flow import (
    InitialSummaryDocument,
    StandardizedFileDocument,
)

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


def slugify(name: str) -> str:
    """Convert a filename to a URL-safe slug.

    Takes the base filename (without extension), converts to lowercase,
    replaces non-alphanumeric characters with hyphens, and strips leading/trailing hyphens.

    Args:
        name: Original filename

    Returns:
        Slugified version suitable for URLs/filenames
    """
    base = Path(name).stem.lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "file"


@pipeline_task
async def standardize_files(
    input_documents: DocumentList,
    initial_summary: InitialSummaryDocument,
    model: ModelName,
    project_name: str,
) -> list[StandardizedFileDocument]:
    """Convert each input file to standardized English Markdown.

    Processes each user-provided document, converting it to clean English Markdown
    with YAML front-matter containing metadata, improved summaries, and key information.
    Uses the initial summary as static context for efficient provider caching.

    Args:
        input_documents: User-provided files to standardize
        initial_summary: Initial project summary for context
        model: Model to use for conversion (typically small_model)
        project_name: Project name for context

    Returns:
        List of StandardizedFileDocument instances with slugified filenames
    """
    results: list[StandardizedFileDocument] = []

    # Reuse static context across calls for provider caching
    # This reduces token usage when processing multiple files
    static_context = AIMessages([initial_summary])

    for doc in input_documents:
        # Get prompt template and render with project name
        prompt = prompt_manager.get(
            "standardize_files", project_name=project_name, file_name=doc.name
        )

        # Dynamic messages per file
        messages = AIMessages([doc, prompt])

        # Generate standardized Markdown with context caching
        res = await llm.generate(
            model=model,
            context=static_context,  # Static, cacheable
            messages=messages,  # Dynamic per file
        )

        # Create output filename with slug (no path separators allowed in document names)
        out_name = f"{slugify(doc.name)}.md"

        # Create standardized document
        results.append(StandardizedFileDocument.create(name=out_name, content=res.content))

        logger.debug(f"Standardized {doc.name} -> {out_name}")

    return results
