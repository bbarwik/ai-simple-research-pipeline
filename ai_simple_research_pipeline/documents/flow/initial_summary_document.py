from enum import StrEnum

from ai_pipeline_core import FlowDocument


class InitialSummaryDocument(FlowDocument):
    """Initial due diligence summary with project overview and source analysis."""

    class FILES(StrEnum):
        INITIAL_SUMMARY = "initial_summary.json"
