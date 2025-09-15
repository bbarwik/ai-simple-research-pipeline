from enum import StrEnum

from ai_pipeline_core import FlowDocument


class FinalReportDocument(FlowDocument):
    """Final due diligence report in markdown format."""

    class FILES(StrEnum):
        SHORT_REPORT = "short_report.md"
        FULL_REPORT = "full_report.md"
