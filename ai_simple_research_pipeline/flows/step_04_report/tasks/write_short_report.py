from ai_pipeline_core import (
    AIMessages,
    Document,
    DocumentList,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)

from ai_simple_research_pipeline.documents.flow import FinalReportDocument

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


@pipeline_task
async def write_short_report(
    standardized_documents: DocumentList,
    initial_summary: Document,
    risks: Document,
    opportunities: Document,
    questions: Document,
    model: ModelName,
) -> FinalReportDocument:
    """Generate concise due-diligence report (up to 5 pages) from all artifacts."""
    prompt = prompt_manager.get("write_short_report")

    # Context: all content for provider caching (static documents)
    context = AIMessages(
        list(standardized_documents) + [initial_summary, risks, opportunities, questions]
    )

    # Messages: the dynamic prompt
    messages = AIMessages([prompt])

    # Generate short report using context/messages split for caching
    result = await llm.generate(
        model=model,
        context=context,
        messages=messages,
    )

    return FinalReportDocument.create(
        name=FinalReportDocument.FILES.SHORT_REPORT, content=result.content
    )
