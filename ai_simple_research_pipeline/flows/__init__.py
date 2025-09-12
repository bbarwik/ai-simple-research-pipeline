"""Pipeline flows for due diligence report generation."""

from .step_01_summary import summary_flow
from .step_02_standardization import standardization_flow
from .step_03_review import review_flow
from .step_04_report import report_flow

FLOWS = [summary_flow, standardization_flow, review_flow, report_flow]

__all__ = ["FLOWS"]
