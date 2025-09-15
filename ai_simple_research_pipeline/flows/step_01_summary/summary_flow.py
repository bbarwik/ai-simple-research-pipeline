import asyncio

from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_simple_research_pipeline.documents.flow import (
    InitialSummaryDocument,
    UserInputDocument,
)
from ai_simple_research_pipeline.flow_options import ProjectFlowOptions

from .tasks import create_long_description, create_short_description, create_summary


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

    # First create the initial summary
    summary = await create_summary(
        documents=inputs,
        model=flow_options.core_model,
        project_name=project_name,
    )

    # Then generate descriptions in parallel
    short_desc, long_desc = await asyncio.gather(
        create_short_description(
            summary=summary,
            model=flow_options.core_model,
        ),
        create_long_description(
            summary=summary,
            model=flow_options.core_model,
        ),
    )

    # Return validated output
    return SummaryFlowConfig.create_and_validate_output([summary, short_desc, long_desc])
