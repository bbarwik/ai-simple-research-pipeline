from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_simple_research_pipeline.documents.flow import (
    InitialSummaryDocument,
    ReviewFindingDocument,
    StandardizedFileDocument,
)
from ai_simple_research_pipeline.flow_options import ProjectFlowOptions

from .tasks import generate_findings


class ReviewFlowConfig(FlowConfig):
    """Configuration for investment review flow."""

    INPUT_DOCUMENT_TYPES = [InitialSummaryDocument, StandardizedFileDocument]
    OUTPUT_DOCUMENT_TYPE = ReviewFindingDocument


@pipeline_flow(config=ReviewFlowConfig)
async def review_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    """Generate investment findings: risks, opportunities, and questions.

    Analyzes standardized documents and initial summary to produce
    structured findings for investor due diligence.
    """
    # Get required inputs
    initial_summary = documents.get_by(InitialSummaryDocument.FILES.INITIAL_SUMMARY)
    standardized_docs = documents.filter_by(StandardizedFileDocument)

    # Generate findings using structured output
    risks_doc, opportunities_doc, questions_doc = await generate_findings(
        standardized_documents=standardized_docs,
        initial_summary=initial_summary,
        model=flow_options.core_model,
        project_name=project_name,
    )

    # Return all three finding documents
    return ReviewFlowConfig.create_and_validate_output(
        [
            risks_doc,
            opportunities_doc,
            questions_doc,
        ]
    )
