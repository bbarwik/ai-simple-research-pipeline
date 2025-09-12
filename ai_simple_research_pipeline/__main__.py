from ai_pipeline_core import get_pipeline_logger
from ai_pipeline_core.prefect import serve

from ai_simple_research_pipeline.flows import FLOWS
from ai_simple_research_pipeline.research_pipeline import research_pipeline

logger = get_pipeline_logger(__name__)


def deploy_pipeline():
    logger.info("Starting deployment service...")

    deployments = []
    for flow in [research_pipeline, *FLOWS]:
        deployment_name = flow.name or "unnamed_flow"
        logger.info(f"Creating deployment for flow: {deployment_name}")
        deployments.append(
            flow.to_deployment(
                name=deployment_name,
            )
        )

    logger.info(f"Starting {len(deployments)} deployments...")
    serve(*deployments)


if __name__ == "__main__":
    logger.info("AI Simple Research Pipeline Worker Starting...")
    deploy_pipeline()
