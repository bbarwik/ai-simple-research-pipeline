from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_simple_research_pipeline.documents.flow import (
    InitialSummaryDocument,
    UserInputDocument,
)
from ai_simple_research_pipeline.flow_options import ProjectFlowOptions

from .tasks import create_initial_summary


class SummaryFlowConfig(FlowConfig):
    """Configuration for summary flow."""

    INPUT_DOCUMENT_TYPES = [UserInputDocument]
    OUTPUT_DOCUMENT_TYPE = InitialSummaryDocument


@pipeline_flow(config=SummaryFlowConfig)
async def summary_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    """Process documents through summary flow."""
    # Get input documents
    inputs = documents.filter_by(UserInputDocument)

    # Process with task
    summary = await create_initial_summary(
        documents=inputs,
        model=flow_options.core_model,
        project_name=project_name,
    )

    # Return validated output
    return SummaryFlowConfig.create_and_validate_output([summary])
