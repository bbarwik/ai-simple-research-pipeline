from enum import StrEnum

from ai_pipeline_core import FlowDocument


class ReviewFindingDocument(FlowDocument):
    """Document containing investment review findings (risks, opportunities, or questions)."""

    class FILES(StrEnum):
        RISKS = "risks.json"
        OPPORTUNITIES = "opportunities.json"
        QUESTIONS = "questions.json"
