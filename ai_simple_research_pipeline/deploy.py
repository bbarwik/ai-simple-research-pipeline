from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow
from ai_pipeline_core.prefect import serve

from .documents.flow import FinalReportDocument, UserInputDocument
from .flow_options import ProjectFlowOptions
from .flows import FLOWS


class ResearchPipelineConfig(FlowConfig):
    INPUT_DOCUMENT_TYPES = [UserInputDocument]
    OUTPUT_DOCUMENT_TYPE = FinalReportDocument


@pipeline_flow(config=ResearchPipelineConfig)
async def research_pipeline(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    documents = ResearchPipelineConfig.get_input_documents(documents)
    # it doesn't work yet
    for flow in FLOWS:
        new_documents = await flow(project_name, documents, flow_options)
        documents.extend(new_documents)

    final_documents = documents.filter_by(ResearchPipelineConfig.OUTPUT_DOCUMENT_TYPE)
    return ResearchPipelineConfig.create_and_validate_output(final_documents)


def deploy_pipeline():
    deployments = []
    for flow in [research_pipeline, *FLOWS]:
        deployments.append(
            flow.to_deployment(
                name=flow.name,
            )
        )
    serve(*deployments)


if __name__ == "__main__":
    deploy_pipeline()
