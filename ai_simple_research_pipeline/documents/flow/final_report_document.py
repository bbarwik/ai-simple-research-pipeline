from enum import StrEnum

from ai_pipeline_core import FlowDocument


class FinalReportDocument(FlowDocument):
    """Final due diligence report in markdown format."""

    class FILES(StrEnum):
        FINAL_REPORT = "final_report.md"
