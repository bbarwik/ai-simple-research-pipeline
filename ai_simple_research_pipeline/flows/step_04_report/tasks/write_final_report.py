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
async def write_final_report(
    standardized_documents: DocumentList,
    initial_summary: Document,
    risks: Document,
    opportunities: Document,
    questions: Document,
    model: ModelName,
    project_name: str,
) -> FinalReportDocument:
    """Generate comprehensive due-diligence report from all artifacts."""
    prompt = prompt_manager.get("write_final_report", project_name=project_name)

    # Context: all content for provider caching (static documents)
    context = AIMessages(
        list(standardized_documents) + [initial_summary, risks, opportunities, questions]
    )

    # Messages: the dynamic prompt
    messages = AIMessages([prompt])

    # Generate report using context/messages split for caching
    result = await llm.generate(
        model=model,
        context=context,
        messages=messages,
    )

    return FinalReportDocument.create(
        name=FinalReportDocument.FILES.FINAL_REPORT, content=result.content
    )
