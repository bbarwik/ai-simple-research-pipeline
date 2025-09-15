import asyncio

from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_simple_research_pipeline.documents.flow import (
    InitialSummaryDocument,
    StandardizedFileDocument,
    UserInputDocument,
)
from ai_simple_research_pipeline.flow_options import ProjectFlowOptions

from .tasks import extract_metadata, standardize_content


class StandardizationFlowConfig(FlowConfig):
    """Configuration for standardization flow."""

    INPUT_DOCUMENT_TYPES = [UserInputDocument, InitialSummaryDocument]
    OUTPUT_DOCUMENT_TYPE = StandardizedFileDocument


@pipeline_flow(config=StandardizationFlowConfig)
async def standardization_flow(
    project_name: str, documents: DocumentList, flow_options: ProjectFlowOptions
) -> DocumentList:
    """Convert each user file to English Markdown with improved summaries.

    Takes raw user files and the initial summary, converts each file to
    standardized English Markdown with YAML front-matter containing metadata
    and improved summaries.

    Args:
        project_name: Project identifier
        documents: Input documents (user files and initial summary)
        flow_options: Flow configuration with model selection

    Returns:
        DocumentList containing StandardizedFileDocument instances
    """
    # Get input documents
    inputs = documents.filter_by(UserInputDocument)
    initial_summary = documents.get_by(InitialSummaryDocument.FILES.INITIAL_SUMMARY)

    # Process all files in parallel batches
    results: list[StandardizedFileDocument] = []
    for doc in inputs:
        # Extract metadata and standardize content in parallel for each document
        metadata, content = await asyncio.gather(
            extract_metadata(
                document=doc,
                initial_summary=initial_summary,
                model=flow_options.small_model,
                project_name=project_name,
            ),
            standardize_content(
                document=doc,
                metadata=initial_summary,  # Use initial summary as context for now
                model=flow_options.small_model,
                project_name=project_name,
            ),
        )
        results.extend([metadata, content])

    # Return validated output
    return StandardizationFlowConfig.create_and_validate_output(results)
