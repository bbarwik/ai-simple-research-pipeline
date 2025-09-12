from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_simple_research_pipeline.documents.flow import (
    FinalReportDocument,
    InitialSummaryDocument,
    ReviewFindingDocument,
    StandardizedFileDocument,
)
from ai_simple_research_pipeline.flow_options import ProjectFlowOptions

from .tasks import write_final_report


class ReportFlowConfig(FlowConfig):
    """Configuration for report generation flow."""

    INPUT_DOCUMENT_TYPES = [
        InitialSummaryDocument,
        StandardizedFileDocument,
        ReviewFindingDocument,
    ]
    OUTPUT_DOCUMENT_TYPE = FinalReportDocument


@pipeline_flow(config=ReportFlowConfig)
async def report_flow(
    project_name: str, documents: DocumentList, flow_options: ProjectFlowOptions
) -> DocumentList:
    """Generate comprehensive due-diligence report from all artifacts."""
    # Get specific documents
    initial_summary = documents.get_by(InitialSummaryDocument)
    standardized_docs = documents.filter_by(StandardizedFileDocument)
    risks = documents.get_by(ReviewFindingDocument.FILES.RISKS)
    opportunities = documents.get_by(ReviewFindingDocument.FILES.OPPORTUNITIES)
    questions = documents.get_by(ReviewFindingDocument.FILES.QUESTIONS)

    # Generate final report
    final_report = await write_final_report(
        standardized_documents=standardized_docs,
        initial_summary=initial_summary,
        risks=risks,
        opportunities=opportunities,
        questions=questions,
        model=flow_options.core_model,
        project_name=project_name,
    )

    return ReportFlowConfig.create_and_validate_output([final_report])
