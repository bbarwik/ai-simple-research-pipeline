from ai_pipeline_core import get_pipeline_logger, trace
from ai_pipeline_core.prefect import flow

from ai_simple_research_pipeline.flow_options import ProjectFlowOptions
from ai_simple_research_pipeline.flows import FLOWS

logger = get_pipeline_logger(__name__)


@flow(name="research_pipeline", flow_run_name="research_pipeline-{project_name}")
@trace(name="research_pipeline")
async def research_pipeline(
    project_name: str,
    documents: str,
    flow_options: ProjectFlowOptions,
):
    new_documents = []
    for index, pipeline_flow in enumerate(FLOWS):
        logger.info(f"Starting flow {index + 1} of {len(FLOWS)}: {pipeline_flow.name}")
        flow_config = pipeline_flow.config
        flow_documents = await flow_config.load_documents(documents)
        new_documents = await pipeline_flow(project_name, flow_documents, flow_options)
        logger.info(f"Flow {pipeline_flow.name} finished with {len(new_documents)} new documents")
        await flow_config.save_documents(documents, new_documents)
