from ai_pipeline_core import (
    AIMessages,
    Document,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)

from ai_simple_research_pipeline.documents.flow import InitialSummaryDocument

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


@pipeline_task
async def create_long_description(summary: Document, model: ModelName) -> InitialSummaryDocument:
    """Generate comprehensive project description (500-1000 words) from summary."""
    prompt = prompt_manager.get("create_long_description")

    # Context: summary for caching
    context = AIMessages([summary])
    messages = AIMessages([prompt])

    result = await llm.generate(
        model=model,
        context=context,
        messages=messages,
    )

    return InitialSummaryDocument.create(
        name=InitialSummaryDocument.FILES.LONG_DESCRIPTION,
        content=result.content,
    )
