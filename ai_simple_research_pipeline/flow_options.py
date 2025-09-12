from ai_pipeline_core import FlowOptions, ModelName
from pydantic import Field


class ProjectFlowOptions(FlowOptions):
    """Project-specific flow configuration for startup analysis pipeline."""

    core_model: ModelName = Field(default="google/gemini-2.5-flash")
    small_model: ModelName = Field(default="google/gemini-2.5-flash-lite")
